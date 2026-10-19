# SPDX-License-Identifier: Apache-2.0
import http.client
import json
import secrets
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import Api, ApiError, Application, open_store

BUSINESS = "018f3c4e-7b2a-7c3d-8e9f-0123456789ab"
CHALLENGE = "018f3c4e-7b2a-7c3d-8e9f-dddddddddddd"


class TutorialTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.filename = Path(self.temp.name) / "test.sqlite"
        self.requests = []
        self.state = "sent"
        self.lose_create = False
        self.lose_verify = False
        self.create_http = 202
        self.get_http = 200
        self.code = f"{secrets.randbelow(1000000):06d}"
        self.payload = {"purpose": "login", "channel": "sms", "destination": "+2348012345678", "from": "ONEFUNNEL", "template_key": "login-sms-en-default", "locale": "en"}
        case = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, value):
                self.send_response(status)
                self.send_header("Content-Type", "application/json" if status < 400 else "application/problem+json")
                self.end_headers()
                self.wfile.write(json.dumps(value).encode())

            def problem(self, status, code):
                self.respond(status, {"status": status, "code": code})

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                case.requests.append((self.path, self.headers.get("Idempotency-Key"), raw))
                case.assertEqual(self.headers["Authorization"], "Bearer offline-test-token")
                path = f"/v1/businesses/{BUSINESS}/otp/challenges"
                if self.path == path:
                    case.assertEqual(json.loads(raw), case.payload)
                    if case.lose_create:
                        case.lose_create = False
                        self.close_connection = True
                        return
                    self.respond(case.create_http, case.challenge())
                else:
                    case.assertEqual(self.path, path + "/" + CHALLENGE + "/verify")
                    case.assertIsNone(self.headers.get("Idempotency-Key"), "verify does not support idempotency")
                    if case.state == "expired":
                        self.problem(422, "otp_challenge_expired")
                    elif case.state == "locked":
                        self.problem(429, "otp_challenge_locked")
                    elif case.state == "invalidated":
                        self.problem(409, "otp_challenge_invalidated")
                    elif case.state == "verified":
                        self.problem(409, "otp_challenge_consumed")
                    elif json.loads(raw)["code"] != case.code:
                        self.problem(422, "otp_verification_failed")
                    else:
                        case.state = "verified"
                        if case.lose_verify:
                            case.lose_verify = False
                            self.close_connection = True
                            return
                        self.respond(200, {"id": CHALLENGE, "status": "verified", "purpose": "login", "verified_at": "2026-10-18T13:00:05Z"})

            def do_GET(self):
                case.assertEqual(self.path, f"/v1/businesses/{BUSINESS}/otp/challenges/{CHALLENGE}")
                if case.get_http == 200:
                    self.respond(200, case.challenge())
                else:
                    self.problem(case.get_http, "service_unavailable")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api = Api(f"http://127.0.0.1:{self.server.server_port}", BUSINESS, "offline-test-token")
        self.db = open_store(self.filename)
        self.app = Application(self.db, self.api)

    def challenge(self):
        return {"id": CHALLENGE, "business_id": BUSINESS, "status": self.state,
                "purpose": "login", "channel": "sms", "delivery_mode": "template",
                "code_length": 6, "expires_at": "2026-10-18T13:05:00Z",
                "created_at": "2026-10-18T13:00:00Z", "updated_at": "2026-10-18T13:00:01Z"}

    def restart(self):
        self.db.close()
        self.db = open_store(self.filename)
        self.app = Application(self.db, self.api)

    def create(self):
        return self.app.create("login-1001", "user-42", self.payload)

    def tearDown(self):
        self.db.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def test_lost_create_reuses_key_and_body_after_restart(self):
        self.lose_create = True
        with self.assertRaises(http.client.RemoteDisconnected):
            self.create()
        self.restart()
        result = self.create()
        self.assertEqual(result["challenge_id"], CHALLENGE)
        self.assertEqual(self.requests[0], self.requests[1])
        self.assertEqual(self.create()["challenge_id"], CHALLENGE)
        self.assertEqual(len(self.requests), 2)
        with self.assertRaisesRegex(ValueError, "different request"):
            self.app.create("login-1001", "user-42", {**self.payload, "locale": "fr"})

    def test_verify_binds_saved_challenge_subject_and_purpose(self):
        self.create()
        with self.assertRaisesRegex(ValueError, "matching local session"):
            self.app.verify("login-1001", "other-user", self.code)
        result = self.app.verify("login-1001", "user-42", self.code)
        self.assertEqual(result["verification_state"], "verified")
        self.assertEqual(result["challenge_id"], CHALLENGE)
        self.assertEqual(len(self.requests), 2)
        self.restart()
        with self.assertRaisesRegex(ValueError, "already completed"):
            self.app.verify("login-1001", "user-42", self.code)
        self.assertEqual(len(self.requests), 2, "duplicate local verification must not POST again")
        serialized = json.dumps(dict(self.app.session("login-1001", "user-42")))
        self.assertNotIn(self.code, serialized)
        self.assertNotIn("offline-test-token", serialized)

    def test_wrong_code_allows_deliberate_new_attempt(self):
        self.create()
        wrong = "000000" if self.code != "000000" else "111111"
        with self.assertRaises(ApiError) as error:
            self.app.verify("login-1001", "user-42", wrong)
        self.assertEqual((error.exception.http_status, error.exception.code), (422, "otp_verification_failed"))
        self.assertEqual(self.app.session("login-1001", "user-42")["verification_state"], "idle")
        self.assertEqual(self.app.verify("login-1001", "user-42", self.code)["verification_state"], "verified")

    def test_expiry_lock_invalidation_and_consumed_are_not_success(self):
        self.create()
        for status, expected in [("expired", "otp_challenge_expired"), ("locked", "otp_challenge_locked"), ("invalidated", "otp_challenge_invalidated"), ("verified", "otp_challenge_consumed")]:
            with self.subTest(status=status):
                with self.db:
                    self.db.execute("UPDATE sessions SET verification_state='idle',challenge_status='sent'")
                self.state = status
                with self.assertRaises(ApiError) as error:
                    self.app.verify("login-1001", "user-42", self.code)
                self.assertEqual(error.exception.code, expected)
                row = self.app.session("login-1001", "user-42")
                self.assertEqual(row["verification_state"], "blocked")
                self.assertIsNone(row["verified_at"])

    def test_lost_verify_is_uncertain_even_when_get_reports_verified(self):
        self.create()
        self.lose_verify = True
        with self.assertRaises(http.client.RemoteDisconnected):
            self.app.verify("login-1001", "user-42", self.code)
        self.restart()
        result = self.app.status("login-1001", "user-42")
        self.assertEqual(result["challenge_status"], "verified")
        self.assertEqual(result["verification_state"], "uncertain")
        self.assertIsNone(result["verified_at"])
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.app.verify("login-1001", "user-42", self.code)
        self.assertEqual(len(self.requests), 2)

    def test_http_status_scope_and_failed_lookup(self):
        self.create_http = 200
        with self.assertRaises(ApiError) as error:
            self.create()
        self.assertEqual(error.exception.http_status, 200)
        self.assertIsNone(self.app.session("login-1001", "user-42")["challenge_id"])
        self.create_http = 202
        self.create()
        self.get_http = 503
        with self.assertRaises(ApiError):
            self.app.status("login-1001", "user-42")
        self.assertEqual(self.app.session("login-1001", "user-42")["challenge_id"], CHALLENGE)
        with self.assertRaisesRegex(ValueError, "separate database"):
            Application(self.db, Api(self.api.base_url, "other-business", "test"))


if __name__ == "__main__":
    unittest.main()

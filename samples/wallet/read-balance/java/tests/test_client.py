# SPDX-License-Identifier: Apache-2.0
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BUSINESS = "018f3c4e-7b2a-7c3d-8e9f-0123456789ab"


class JavaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        subprocess.run(["javac", "--release", "17", "-d", cls.temp.name, str(Path(__file__).resolve().parents[1] / "src" / "WalletBalance.java")], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.status = 200
        self.seen = []
        case = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                case.seen.append((self.path, self.headers.get("Authorization")))
                self.send_response(case.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                body = json.loads((Path(__file__).resolve().parents[5] / "fixtures/wallet/balance.json").read_text()) if case.status == 200 else {"code": "balance_unavailable"}
                self.wfile.write(json.dumps(body).encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_client(self, base=None):
        return subprocess.run(["java", "-cp", self.temp.name, "WalletBalance"], env={**os.environ, "API_BASE_URL": base or f"http://127.0.0.1:{self.server.server_port}", "BUSINESS_ID": BUSINESS, "ACCESS_TOKEN": "offline-test-token"}, text=True, capture_output=True, timeout=20)

    def test_snapshot(self):
        result = self.run_client()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["available_balance"], "15000.00")
        self.assertEqual(self.seen, [(f"/v1/businesses/{BUSINESS}/wallet/balance", "Bearer offline-test-token")])

    def test_unavailable_is_not_zero(self):
        self.status = 503
        result = self.run_client()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("HTTP 503", result.stderr)
        self.assertNotIn("offline-test-token", result.stderr)

    def test_insecure_origin(self):
        result = self.run_client("http://example.invalid")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.seen, [])


if __name__ == "__main__":
    unittest.main()

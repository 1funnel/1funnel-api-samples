# SPDX-License-Identifier: Apache-2.0
import json
import os
from pathlib import Path
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BUSINESS = "018f3c4e-7b2a-7c3d-8e9f-0123456789ab"


class CurlTest(unittest.TestCase):
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
                self.wfile.write(json.dumps({"available_balance": "15000.00"} if case.status == 200 else {"code": "balance_unavailable"}).encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_request(self, base=None):
        return subprocess.run(["bash", str(Path(__file__).with_name("request.sh"))], env={**os.environ, "API_BASE_URL": base or f"http://127.0.0.1:{self.server.server_port}", "BUSINESS_ID": BUSINESS, "ACCESS_TOKEN": "offline-test-token"}, capture_output=True, text=True, timeout=20)

    def test_success(self):
        result = self.run_request()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("200", result.stdout)
        self.assertIn('"15000.00"', result.stdout)
        self.assertEqual(self.seen, [(f"/v1/businesses/{BUSINESS}/wallet/balance", "Bearer offline-test-token")])

    def test_error(self):
        self.status = 503
        result = self.run_request()
        self.assertEqual(result.returncode, 22)
        self.assertIn("balance_unavailable", result.stdout)

    def test_insecure_origin(self):
        result = self.run_request("http://example.invalid")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.seen, [])


if __name__ == "__main__":
    unittest.main()

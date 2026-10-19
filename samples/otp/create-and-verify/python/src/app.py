# SPDX-License-Identifier: Apache-2.0
"""A terminal OTP exercise; no browser sessions or login tokens are issued."""

import argparse
import getpass
import json
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime


class ApiError(Exception):
    def __init__(self, http_status, code, request_id=None, retry_after=None):
        self.http_status = http_status
        self.code = code
        self.retry_after = retry_after
        super().__init__(f"API HTTP {http_status}, code {code}, request {request_id or 'unknown'}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Api:
    def __init__(self, base_url, business_id, token):
        base = urllib.parse.urlsplit(base_url)
        if base.scheme != "https" and not (
            base.scheme == "http" and base.hostname == "127.0.0.1"
        ):
            raise ValueError("Use HTTPS, or 127.0.0.1 for offline tests")
        if base.username or base.password or base.query or base.fragment or base.path not in ("", "/"):
            raise ValueError("Supply only the API origin")
        self.base_url = base_url.rstrip("/")
        self.business_id = business_id
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)
        self.path = "/v1/businesses/" + urllib.parse.quote(business_id, safe="") + "/otp/challenges"

    def request(self, method, suffix="", body=None, key=None, expected=200):
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if key:
            headers["Idempotency-Key"] = key
        req = urllib.request.Request(
            self.base_url + self.path + suffix,
            data=body.encode("utf-8") if body is not None else None,
            headers=headers, method=method,
        )
        try:
            with self.opener.open(req, timeout=15) as response:
                http_status = response.status
                if http_status != expected:
                    raise ApiError(http_status, "unexpected_http_status", response.headers.get("X-Request-Id"))
                return json.load(response)
        except urllib.error.HTTPError as error:
            try:
                problem = json.loads(error.read(65536))
                code = problem.get("code", "unrecognized_error") if isinstance(problem, dict) else "unrecognized_error"
                # Only expose machine-readable codes, never raw bodies or code values.
                if not isinstance(code, str) or not re.fullmatch(r"[a-z_]{1,80}", code):
                    code = "unrecognized_error"
            except (ValueError, UnicodeError):
                code = "unrecognized_error"
            finally:
                error.close()
            raise ApiError(error.code, code, error.headers.get("X-Request-Id"), error.headers.get("Retry-After")) from None


def validate_timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError()
    except (AttributeError, ValueError):
        raise ValueError("Expected an absolute timestamp") from None


def open_store(filename):
    db = sqlite3.connect(filename, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS configuration(scope TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS sessions(
            session_id TEXT PRIMARY KEY, subject TEXT NOT NULL, body TEXT NOT NULL,
            idem_key TEXT NOT NULL, challenge_id TEXT UNIQUE,
            challenge_status TEXT, expires_at TEXT, code_length INTEGER,
            verification_state TEXT NOT NULL DEFAULT 'idle',
            verified_at TEXT, last_error TEXT
        );
    """)
    return db


class Application:
    def __init__(self, db, api):
        self.db = db
        self.api = api
        scope = json.dumps([api.base_url, api.business_id])
        with db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT scope FROM configuration").fetchone()
            if row and row["scope"] != scope:
                raise ValueError("Use a separate database per API host and business")
            if not row:
                db.execute("INSERT INTO configuration VALUES (?)", (scope,))

    def session(self, session_id, subject):
        row = self.db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row or row["subject"] != subject:
            raise ValueError("No matching local session for this subject")
        return row

    @staticmethod
    def summary(row):
        return {key: row[key] for key in (
            "session_id", "challenge_id", "challenge_status", "expires_at",
            "verification_state", "verified_at", "last_error",
        )}

    def validate_challenge(self, value, row):
        body = json.loads(row["body"])
        if (not isinstance(value, dict) or not isinstance(value.get("id"), str)
                or not value["id"] or value.get("business_id") != self.api.business_id
                or value.get("purpose") != body["purpose"] or value.get("channel") != "sms"
                or value.get("status") not in {"queued", "sent", "verified", "expired", "locked", "invalidated", "failed_delivery"}
                or type(value.get("code_length")) is not int or not 4 <= value["code_length"] <= 12
                or (row["challenge_id"] and value["id"] != row["challenge_id"])):
            raise ValueError("Unexpected challenge resource")
        validate_timestamp(value.get("expires_at"))

    def create(self, session_id, subject, payload):
        if not session_id or not subject or payload.get("channel") != "sms":
            raise ValueError("Supply a local session ID, subject and SMS request")
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("INSERT OR IGNORE INTO sessions(session_id,subject,body,idem_key) VALUES (?,?,?,?)",
                            (session_id, subject, body, str(uuid.uuid4())))
            row = self.session(session_id, subject)
            if row["body"] != body:
                raise ValueError("Session already has a different request")
        if row["challenge_id"]:
            return self.summary(row)
        challenge = self.api.request("POST", body=row["body"], key=row["idem_key"], expected=202)
        self.validate_challenge(challenge, row)
        with self.db:
            self.db.execute("""UPDATE sessions SET challenge_id=?,challenge_status=?,expires_at=?,code_length=?
                WHERE session_id=? AND challenge_id IS NULL""",
                (challenge["id"], challenge["status"], challenge["expires_at"], challenge["code_length"], session_id))
        return self.summary(self.session(session_id, subject))

    def status(self, session_id, subject):
        row = self.session(session_id, subject)
        if not row["challenge_id"]:
            raise ValueError("Resolve the original create request first")
        value = self.api.request("GET", "/" + urllib.parse.quote(row["challenge_id"], safe=""))
        self.validate_challenge(value, row)
        with self.db:
            self.db.execute("UPDATE sessions SET challenge_status=?,expires_at=? WHERE session_id=?",
                            (value["status"], value["expires_at"], session_id))
        # Observing 'verified' is not proof of a new successful code submission.
        return self.summary(self.session(session_id, subject))

    def verify(self, session_id, subject, code):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.session(session_id, subject)
            if not row["challenge_id"]:
                raise ValueError("Resolve the original create request first")
            if row["verification_state"] != "idle":
                raise ValueError("Verification already completed, blocked or uncertain; inspect status and recover")
            if row["challenge_status"] in {"verified", "expired", "locked", "invalidated"}:
                raise ValueError("Challenge is terminal; do not submit another code")
            if not isinstance(code, str) or not re.fullmatch(r"[0-9A-Za-z]{4,12}", code) or len(code) != row["code_length"]:
                raise ValueError("Code format does not match the challenge")
            self.db.execute("UPDATE sessions SET verification_state='uncertain',last_error=NULL WHERE session_id=?", (session_id,))
        try:
            result = self.api.request("POST", "/" + urllib.parse.quote(row["challenge_id"], safe="") + "/verify",
                                      body=json.dumps({"code": code}), expected=200)
        except ApiError as error:
            terminal = {
                (422, "otp_challenge_expired"): "expired",
                (409, "otp_challenge_consumed"): "verified",
                (409, "otp_challenge_invalidated"): "invalidated",
                (429, "otp_challenge_locked"): "locked",
            }
            pair = (error.http_status, error.code)
            with self.db:
                if pair == (422, "otp_verification_failed"):
                    # A deliberate new user attempt is allowed; no automated code retry.
                    self.db.execute("UPDATE sessions SET verification_state='idle',last_error=? WHERE session_id=?", (error.code, session_id))
                elif pair in terminal:
                    self.db.execute("UPDATE sessions SET verification_state='blocked',challenge_status=?,last_error=? WHERE session_id=?", (terminal[pair], error.code, session_id))
            raise
        if (not isinstance(result, dict) or result.get("id") != row["challenge_id"]
                or result.get("purpose") != json.loads(row["body"])["purpose"]
                or result.get("status") != "verified"):
            raise ValueError("Unexpected verification result; treat outcome as uncertain")
        validate_timestamp(result.get("verified_at"))
        with self.db:
            self.db.execute("UPDATE sessions SET verification_state='verified',challenge_status='verified',verified_at=? WHERE session_id=?", (result["verified_at"], session_id))
        return self.summary(self.session(session_id, subject))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("create", "verify", "status", "inspect"))
    parser.add_argument("session")
    parser.add_argument("subject")
    parser.add_argument("request_file", nargs="?")
    args = parser.parse_args()
    db = open_store(os.environ.get("DB_PATH", "otp.sqlite"))
    try:
        app = Application(db, Api(os.environ.get("API_BASE_URL", "https://api.sandbox.1-funnel.org"), os.environ["BUSINESS_ID"], os.environ["ACCESS_TOKEN"]))
        if args.command == "create":
            if not args.request_file:
                parser.error("create requires a request JSON file")
            with open(args.request_file, encoding="utf-8") as file:
                result = app.create(args.session, args.subject, json.load(file))
        elif args.command == "verify":
            result = app.verify(args.session, args.subject, getpass.getpass("Code received by the test recipient: "))
        elif args.command == "status":
            result = app.status(args.session, args.subject)
        else:
            result = app.summary(app.session(args.session, args.subject))
        print(json.dumps(result, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Avoid printing URL errors or library exceptions that might include bodies.
        if isinstance(error, (ApiError, ValueError, KeyError)):
            print(str(error))
        else:
            print("Request or storage failed. Keep the session and inspect its state before retrying.")
        raise SystemExit(1)

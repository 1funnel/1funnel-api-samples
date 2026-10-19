# Python OTP challenge application

Runnable companion to [Verify an OTP challenge with Python](https://developers.1-funnel.org/guides/tutorials/otp-python).
Requires Python 3.11 or later; no pip packages are needed. This is a terminal
application exercise using standard HTTP and SQLite APIs, not an official SDK
or a complete browser login system.

## Test without credentials

From this directory:

```bash
python3 -m unittest discover -s tests -v
```

Tests use a local HTTP stub and temporary SQLite database. They send no SMS.
They cover persisted create retries after a lost response/restart, stable keys
and payloads, saved challenge IDs, subject binding, duplicate verification,
wrong codes, expiry, lockout, invalidation, consumed codes, unexpected HTTP
status, failed lookups and a lost verify response. Verification codes and access
tokens are not written to the application database. Local tests demonstrate
client behavior; they cannot prove platform delivery, OTP policy or billing.

## Run with approved Sandbox credentials

Follow the tutorial for access, sender and recipient prerequisites. In this directory:

```bash
umask 077
export API_BASE_URL=https://api.sandbox.1-funnel.org
export BUSINESS_ID='<issued-business-id>'
export ACCESS_TOKEN='<issued-access-token>'
export DB_PATH="$PWD/otp.sqlite"
```

Create private `request.json` using an approved OTP template key:

```json
{
  "purpose": "login",
  "channel": "sms",
  "destination": "+2348012345678",
  "from": "ONEFUNNEL",
  "locale": "en",
  "template_key": "<approved-otp-template-key>"
}
```

Replace all sample values. This `template_key` selects an OTP template; it is
not an SMS `template_id`. Alternatively remove `template_key` and use inline
`message` containing `{{code}}` if your business policy allows inline content.
Do not provide both selectors. See the linked tutorial for an inline example.

```bash
python3 src/app.py create login-1001 user-42 request.json
python3 src/app.py inspect login-1001 user-42
python3 src/app.py verify login-1001 user-42
python3 src/app.py status login-1001 user-42
```

`verify` prompts without echoing the entered code. Use the code delivered to the
test recipient. Never put a code in shell arguments or add it to `request.json`.
OneFunnel does not return the code in create or GET responses. `create` requires
HTTP 202; it saves the returned challenge ID and expiry. `verify` uses that ID in
the URL and requires HTTP 200 with matching ID, purpose and `status: verified`.
The request body contains the code alone because the URL supplies correlation.

`login-1001` is a stable local operation/session ID. `user-42` represents the
application user; it must come from trusted application context in a real web
integration. The terminal operator supplies it in this exercise. This comparison
is not authentication or authorization. The example issues no login tokens.

## Recovery

- Lost create response: rerun the exact create command and file with the same
  database, session and subject. The saved key/body are reused. A saved challenge
  skips another POST; a changed subject or payload is rejected. Preserve state
  beyond the public seven-day replay window and investigate unresolved acceptance.
- Wrong code: the API error `otp_verification_failed` leaves the local attempt
  state `idle`; a deliberate new recipient submission is permitted. The example
  does not automatically retry a code or bypass the API attempt limit.
- Expired, locked, invalidated or consumed: verification is blocked and its API
  error code recorded. HTTP 409 `otp_challenge_consumed` is not a new success.
- Lost verify response or process exit during verify: `verification_state` stays
  `uncertain`. Use `status` to inspect the challenge. Even if GET reports verified,
  this example keeps local proof uncertain and issues no login token. Resolve it
  through your application's recovery policy; do not blindly repeat verify or
  update the database to manufacture success.
- HTTP 429: inspect the code and respect `Retry-After`. Lockout and rate limiting
  are different outcomes. HTTP 401/403 require credential/grant investigation.

After an expired or blocked flow, begin an explicitly new user-approved attempt
with a new local session ID and key according to your product policy. Do not
create another challenge merely because a network response was uncertain.
Resend/invalidate are intentionally separate operations in the canonical guides;
this application does not silently perform either one.

## Operational boundary

Use one local SQLite database per API host/business, on persistent local disk.
The program creates new files privately, but existing directory and backup
permissions remain your responsibility. Destination numbers and request content
are persisted; establish retention and protect disk/backups. No code, hash or
access token is stored. The sample does not expose an HTTP route.

Before adapting this to a web application, bind user/session identity on the
server, protect browser actions against CSRF and enumeration, apply abuse/rate
controls, and add secure session issuance with its own transactional/recovery
design. A successful OTP check is not sufficient by itself to implement login,
account recovery or a financial authorization flow. Keep the API's expiry and
attempt policy authoritative; do not invent a fixed TTL or unlimited retries.

## Configuration

See `.env.example` for the required environment variables. The sample reads
exported variables; it does not automatically load `.env` files. Keep real
credentials and local databases outside source control.

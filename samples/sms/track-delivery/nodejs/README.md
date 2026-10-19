# SMS status receiver for Node.js

Runnable companion to [Build an SMS status receiver](https://developers.1-funnel.org/guides/tutorials/sms-status-node).
This is an application example using built-in HTTP, crypto and SQLite APIs, not an official SDK.
Requires Node.js 24; no npm packages are needed. SQLite may print an experimental API warning.

## Test without credentials

```bash
node --test tests/app.test.mjs
```

The test runs an HTTP API stub and signed webhook deliveries on loopback with a
temporary SQLite database. It makes no live API calls or SMS sends. It verifies
persisted idempotency after a lost response and restart, raw-body signature checks,
expired timestamps/keys, rotation overlap, business and event-ID checks, duplicate
receipt, storage failure, worker retry, out-of-order notifications and GET recovery.
The stub demonstrates client behavior; it cannot prove platform delivery or billing.

## Run with approved Sandbox access

Follow the linked tutorial for credentials, endpoint registration and HTTPS routing.
Use separate terminals for the receiver, a send and the worker. Run all commands
from this directory, with the same absolute `DB_PATH` and environment variables.

```bash
umask 077
export API_BASE_URL=https://api.sandbox.1-funnel.org
export BUSINESS_ID='<issued-business-id>'
export ACCESS_TOKEN='<issued-access-token>'
export DB_PATH="$PWD/sms-status.sqlite"
export WEBHOOK_KEYS_FILE="$PWD/keys.json"
node src/app.mjs serve
```

Create `request.json` with your authorized sender and test recipient:

```json
{
  "from": "ONEFUNNEL",
  "to": "+2348012345678",
  "classification": "transactional",
  "message": "Your order ORD-1001 is confirmed."
}
```

Create private `keys.json` using the endpoint signing secret supplied by OneFunnel:

```json
{
  "1": {
    "secret": "<issued-signing-secret>",
    "validFrom": 0,
    "validUntil": 4102444800
  }
}
```

The end date is a configurable bound, not a OneFunnel secret lifetime. During
operator-coordinated rotation install the new version and the agreed validity
windows; remove the old version when retired. Restart the receiver after changing
this file. Restrict its permissions (`chmod 600 keys.json`); do not commit secrets.

```bash
node src/app.mjs send order-1001 request.json
node src/app.mjs inspect
node src/app.mjs work
node src/app.mjs inspect
node src/app.mjs reconcile order-1001
```

`send` checks HTTP 202, saves the message ID and records acceptance; it does not
claim delivery. Repeat the exact command and file after a lost response to reuse
the persisted key. Never delete the database or change the operation ID to retry.
A changed payload with that operation ID is rejected. A saved message ID skips
another POST. After the public seven-day replay window, an uncertain send needs
investigation rather than a new key: use the idempotency recovery guide.

`serve` binds `127.0.0.1:8080` and accepts `POST /hooks/1funnel`. Configure a trusted
HTTPS reverse proxy/tunnel to this path and preserve the raw body and signature
headers. It returns 204 only after SQLite stores the event, including duplicate
receipts; it returns 503 if storage fails. It accepts only the three subscribed
SMS message event types. Unknown-message events remain pending until the send ID
has been recovered. `inspect` shows whether `processed_at` is still null.

`work` processes up to 50 stored events and exits. Run exactly one worker command
at a time, and repeat it periodically in this exercise. Do not overlap it with
`reconcile`. Each event triggers GET of the current resource; event arrival order
does not directly change the saved status. A failed GET leaves the event pending.
`reconcile` explicitly retrieves current state if a webhook is missing; it never
submits another SMS. Respect API rate limits and Retry-After before retrying work.

## Operational boundary

This is a single-machine teaching application. It persists message bodies and
recipient numbers in SQLite: restrict database, directory and backup permissions,
set an appropriate retention policy and protect the disk. Use a persistent local
disk, one database per host/business and synchronized system time. Do not put WAL
files on a shared network volume. Only the webhook path should be exposed publicly.
The example has no public send/admin HTTP routes.

Before production, add supervised scheduling with backoff, bounded inbox retention,
monitoring for pending/unknown events, backup recovery, access controls and capacity
limits. Replace the single-worker assumption with a reviewed claim/lease design if
you scale workers. No external business side effects occur in this example; adding
them requires its own idempotent transaction/outbox design. A saved REST snapshot is
an observation at `checked_at`, not a guarantee of future status or final billing.

## Configuration

See `.env.example` for the required environment variables. The sample reads
exported variables; it does not automatically load `.env` files. Keep real
credentials and local databases outside source control.

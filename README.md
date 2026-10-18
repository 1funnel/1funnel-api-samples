# 1Funnel API samples

Runnable examples for integrating with the [1Funnel API](https://developers.1-funnel.org).
These are application samples using standard HTTP clients, not official SDKs.

## Choose a language and task

- [JavaScript / Node.js: SMS status receiver](javascript/sms-status-receiver/)
  saves send intent, verifies webhook signatures, persists an inbox and retrieves
  current message status. Requires Node.js 24.
- [Python: OTP challenge verification](python/otp-challenge/) saves a challenge
  against a local user/session and handles successful, rejected and uncertain
  verification outcomes. Requires Python 3.11 or later.
- [Java: read wallet balance](java/wallet-balance/) retrieves a balance snapshot
  with Java 17's standard HTTP client. Requires JDK 17 or later.
- [cURL: read wallet balance](curl/wallet-balance/) makes a read-only API request
  and shows its HTTP status and response body. Requires Bash and cURL 7.76 or later.

Each sample has its own README and offline tests. Install only the runtime for
that sample; no access to the developer portal's source repository is needed.
The examples intentionally cover different tasks. Language coverage is not yet
identical across all API operations.

```bash
git clone https://github.com/1funnel/1funnel-api-samples.git
cd 1funnel-api-samples
```

## Test without credentials

Run the commands for your installed runtimes from the repository root:

```bash
node --test javascript/sms-status-receiver/app.test.mjs
python3 -m unittest discover -s python/otp-challenge -p test_app.py -v
python3 java/wallet-balance/test_client.py
python3 curl/wallet-balance/test_request.py
```

Java and cURL tests use a Python 3.11+ HTTP fixture. The Java test also compiles
its companion client, so a JDK is required. All tests use
loopback HTTP fixtures and temporary files. They do not contact the live API or
send SMS. CI runs JavaScript, Python, Java and cURL tests independently.

## Make a Sandbox request

Obtain approved credentials and a business grant using the
[Quickstart](https://developers.1-funnel.org/getting-started/quickstart).
Set environment variables locally using the sample README. API access is
separate from this repository's public availability. Never commit tokens,
signing secrets, OTP codes, recipient data or local databases.

Start with a read-only wallet example if you have `wallet.balance.read`.
SMS and OTP examples need their own permissions, authorized senders and permitted
recipients. HTTP 202 confirms asynchronous acceptance, not SMS delivery.

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for sample layout, verification requirements
and pull requests. New language folders are welcome when they include a runnable
sample, offline tests and clear recovery behavior. Track gaps in GitHub issues
rather than publishing empty language scaffolds.

Use issues for reproducible sample bugs and feature requests. For API access or
account questions, use [1Funnel Support](https://developers.1-funnel.org/resources/support).
Report security vulnerabilities privately using [SECURITY.md](SECURITY.md).

## License

Licensed under the [Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE).

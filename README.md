# OneFunnel API samples

Runnable examples for the [OneFunnel API](https://developers.1-funnel.org), organized
by **API area → developer task → language**. These use ordinary HTTP clients,
not official SDKs. See [structure and maintenance](docs/structure.md) for the
layout, sample types and CI conventions.

## Choose a task

- **Track SMS delivery:** [Node.js application](samples/sms/track-delivery/nodejs/)
  persists send intent, verifies webhook signatures and saves current status.
- **Create and verify an OTP:** [Python application](samples/otp/create-and-verify/python/)
  saves challenge/user correlation and handles rejected or uncertain verification.
- **Read wallet balance:** [Java request example](samples/wallet/read-balance/java/)
  or [cURL request example](samples/wallet/read-balance/curl/).

## Browse by language

- [Node.js](samples/sms/track-delivery/nodejs/) — Node.js 24.
- [Python](samples/otp/create-and-verify/python/) — Python 3.11+.
- [Java](samples/wallet/read-balance/java/) — JDK 17+.
- [cURL](samples/wallet/read-balance/curl/) — Bash and cURL 7.76+.

Only implemented combinations appear here. Language coverage is not identical
across tasks. [The catalog](samples/catalog.json) records each sample's type,
runtime, location and offline test command.

```bash
git clone https://github.com/1funnel/1funnel-api-samples.git
cd 1funnel-api-samples
```

## Run independently

Open your sample's README and follow its setup, source and test commands. Each
has `src/`, `tests/` and a placeholder `.env.example`. There is no requirement
to install other language runtimes to run the client you choose. The Java and
cURL offline test harnesses additionally require Python; their clients do not.
No sample automatically loads environment files.

For repository maintenance, optional commands from the root are:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 scripts/run-samples.py --language nodejs
python3 scripts/run-samples.py --language python
python3 scripts/run-samples.py --language java
python3 scripts/run-samples.py --language curl
```

The maintenance runner requires Python 3.11+ and the selected sample's runtime.
All tests use loopback HTTP fixtures and temporary storage. No live API calls or
SMS sends occur. CI tests affected samples across supported runtime versions;
shared changes test everything. The stable merge check is `samples-ci`.

## Make a Sandbox request

Obtain approved credentials and a business grant using the
[Quickstart](https://developers.1-funnel.org/getting-started/quickstart).
Public sample availability does not grant API access. Start with a read-only
wallet request if you have `wallet.balance.read`. SMS and OTP examples need
additional permissions, authorized senders and permitted recipients. HTTP 202
means asynchronous acceptance, not SMS delivery. Never commit tokens, signing
secrets, OTP codes, recipient data or local databases.

## Contribute and get help

See [CONTRIBUTING.md](CONTRIBUTING.md) for new tasks and languages, and
[SECURITY.md](SECURITY.md) for private vulnerability reporting. Use issues for
reproducible sample bugs or proposals. For API access and account questions,
contact [OneFunnel Support](https://developers.1-funnel.org/resources/support).

## Improve the examples and documentation

Use the [issue chooser](https://github.com/1funnel/1funnel-api-samples/issues/new/choose)
for sample bugs, documentation corrections, new languages/tutorials or feature
suggestions. Small sample fixes can be direct pull requests.
[Author a full tutorial](docs/tutorial-authoring.md) with runnable code, tests
and a Markdown walkthrough; maintainers handle reviewed portal publication.
Use portal Support for private account issues and SECURITY.md for confidential
vulnerability reports.

## License

[Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE).

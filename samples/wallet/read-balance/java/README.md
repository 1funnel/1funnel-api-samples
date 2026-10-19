# Read wallet balance with Java

Requires JDK 17 or later. The client uses Java's standard HTTP library and needs
no Maven/Gradle dependencies. See the [wallet guide](https://developers.1-funnel.org/guides/wallet/balance)
and [operation reference](https://developers.1-funnel.org/api-reference/wallet/retrieve-wallet-balance).

## Run

From this directory, with approved Sandbox credentials and `wallet.balance.read`:

```bash
export BUSINESS_ID='<issued-business-id>'
export ACCESS_TOKEN='<issued-access-token>'
export API_BASE_URL=https://api.sandbox.1-funnel.org
java src/WalletBalance.java
```

The client requires HTTP 200 and prints the balance snapshot as JSON. Monetary
amounts remain decimal strings; it does not parse them as floating-point numbers.
The snapshot is an observation at `as_of`, not a reservation or a promise of
funds for a later send. A failed request exits nonzero; it does not invent zero
balances. Error bodies and tokens are not printed. HTTP redirects are not followed.

## Offline tests

With a JDK and Python 3.11+ installed:

```bash
python3 tests/test_client.py
```

The Python harness compiles the Java client in a temporary directory and runs it
against a loopback HTTP fixture. Tests check the authorization/path, HTTP 200
handling, HTTP 503 failure without a fabricated balance, and rejection of an
insecure non-loopback origin. No live API requests are made.

## Configuration

See `.env.example` for the required environment variables. The sample reads
exported variables; it does not automatically load `.env` files. Keep real
credentials and local databases outside source control.

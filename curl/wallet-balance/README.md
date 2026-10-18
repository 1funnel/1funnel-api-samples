# Read wallet balance with cURL

Requires Bash and cURL 7.76 or later (`--fail-with-body`). With approved Sandbox
credentials and `wallet.balance.read`, run from this directory:

```bash
export BUSINESS_ID='<issued-business-id>'
export ACCESS_TOKEN='<issued-access-token>'
export API_BASE_URL=https://api.sandbox.1-funnel.org
bash request.sh
```

The response includes HTTP headers and the JSON body. HTTP 200 returns a balance
snapshot; errors return a nonzero cURL exit code and the API problem body. There
is no custom response-checking snippet. The command does not follow redirects,
disable TLS verification, or invent a zero balance after a failure.

Treat monetary values as decimal strings and check the snapshot's `as_of`.
See the [wallet guide](https://developers.1-funnel.org/guides/wallet/balance)
and [operation reference](https://developers.1-funnel.org/api-reference/wallet/retrieve-wallet-balance).
Do not paste credentials or account response data into public issues.

## Offline tests

With Python 3.11+ installed:

```bash
python3 test_request.py
```

Tests use a loopback HTTP fixture. No live API request is made.

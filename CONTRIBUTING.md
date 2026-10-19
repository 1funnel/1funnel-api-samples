# Contributing to 1Funnel API samples

Open an issue to discuss a substantial example or language addition. Small fixes
can go directly to a pull request. Please keep one task per pull request.

## Layout

Use `samples/<api-area>/<task>/<language>/`, such as
`samples/otp/create-and-verify/python/`. Follow [the structure conventions](docs/structure.md). Each language sample owns its
runtime requirements, implementation, README and offline tests. Root tooling
must not force users to install every language just to run one example.

The README must explain setup, permissions, environment variables, commands,
expected HTTP status, asynchronous outcomes, failure recovery and the boundary
between a teaching application and production deployment. Link to canonical
API documentation instead of copying an API contract into this repository.

## Implementation requirements

- Use the public hosts, paths and fields in the published API reference.
- Prefer standard libraries; justify additional dependencies and pin them.
- Keep credentials and signing secrets in local environment/configuration.
- Never log or persist plaintext OTP codes or commit live/customer data.
- Persist a supported operation's idempotency key before its first request.
- Check the operation's exact success status; acceptance is distinct from delivery.
- Verify webhook raw bytes, timestamps, secret versions and envelope IDs before
  processing. Persist acceptance before acknowledging delivery.
- Demonstrate the relevant failure path with an offline HTTP test. Do not silently
  retry non-idempotent operations, weaken TLS or invent API error codes.
- Do not describe a sample HTTP client as an official SDK.

## Before opening a PR

Run the sample's offline tests, inspect the diff for credentials and data, and
update its README and root language index. Add a corresponding CI job for a new
runtime. Tests must run without API credentials and must not send live SMS.
A live Sandbox exercise should be separately identified with prerequisites and
explicit operator intent; never make it a default test step.

Maintainers review behavior against the published contract. Please include what
changed, the test command/results and any limitations in the PR description.

Register every sample in `samples/catalog.json`. Include `src/`, `tests/` and
a placeholder `.env.example`. Classify it as a request or application, keep
root task/language navigation current, and run the catalog/planner tests. A new
runtime job must feed the stable `samples-ci` gate; do not add a new required
branch-check name. Shared fixtures must remain synthetic test data.

## Choose a contribution route

- For a sample bug, use the sample bug issue template; a small fix can be a direct
  PR with a reproduction and offline test results.
- For unclear portal or README instructions, use the documentation issue template
  and include the page URL/path and proposed correction. The portal source is
  private; maintainers apply approved portal changes there.
- For a sample, language or complete tutorial, use the proposal template. Follow
  [the tutorial authoring instructions](docs/tutorial-authoring.md) for a full
  application walkthrough and place its draft in the sample's `tutorial.md`.
- For developer-experience or API improvements, use the feature suggestion
  template. Proposals do not change the published API contract or promise dates.
- For account access and request-specific diagnostics, use portal Support.
- For vulnerabilities, use private reporting as described in SECURITY.md.

Maintainers may request changes before accepting contributions. Accepted samples
and tutorial drafts do not automatically publish in the portal; maintainers
prepare a reviewed portal PR and link its publication back to the contribution.
Contributions use Apache-2.0; attribution can be requested in the PR.
Keep discussion respectful and focused on developer needs and reproducible facts.

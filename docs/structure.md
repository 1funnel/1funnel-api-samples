# Sample structure and maintenance

## Find a task, choose a language

Runnable examples live at `samples/<api-area>/<task>/<language>/`. Use stable,
lowercase directory names. The supported language identifiers currently are
`nodejs`, `python`, `java` and `curl`. Add another when its first working sample
is ready; do not publish empty task or language folders as promises.

Use an API area such as `sms`, `otp`, `wallet` or `webhooks`. Name the task for
the developer outcome, for example `send-message`, `create-and-verify` or
`track-delivery`. A cross-domain application belongs under its primary outcome:
the SMS status receiver belongs under SMS even though it consumes webhooks.

Each language directory contains:

- `README.md`: prerequisites, permissions, setup, run/test commands, expected
  results, recovery and operational boundaries.
- `.env.example`: placeholders only. State explicitly whether an environment-file
  loader exists; current samples read exported variables without loading files.
- `src/`: runnable source, including shell commands for cURL examples.
- `tests/`: offline tests with synthetic data and temporary local storage.
- The language's manifest/build files when needed. Do not introduce dependencies
  just to make every directory look identical. A dependency-free Node sample may
  use `package.json` scripts without requiring `npm install`.

## Small requests and complete applications

`samples/catalog.json` classifies each entry as `request` or `application`.
A request example demonstrates one API operation and its success/failure result.
An application joins multiple operations with persisted correlation, idempotency
and recovery. Do not label a request snippet a complete production integration.

The catalog is the inventory used by repository CI. Add a unique ID, API area,
task, language, kind, runtime, path and an argument-array offline test command.
The root README offers task and language navigation; maintain both when adding
or moving an entry. Canonical API behavior and schemas belong in the public
portal, not in a second contract maintained here.

## Independent samples

A developer can run a sample directly using its own README and runtime. Root
scripts are optional maintenance conveniences, not runtime imports or a private
client framework. Shared `fixtures/` may contain synthetic JSON reused by tests.
Wallet tests use `fixtures/wallet/balance.json`; running those tests requires the
repository checkout. Shared fixtures must never become production defaults.
Do not commit real credentials, signing keys, OTP codes, recipients or databases.

Avoid sharing application plumbing between samples. A developer should be able
to understand and copy the application's behavior without learning an internal
framework. Document additional test runtimes honestly: the Java and cURL tests
use a Python HTTP fixture, but running their clients does not require Python.

## Selective CI and stable merge requirements

`scripts/ci-plan.py` selects samples from changed paths. A sample-local change
selects that sample; shared fixtures, catalog, scripts, workflows, unknown paths
or unavailable comparison history conservatively select all samples. Renames
are treated as deletion plus addition, so migrations cannot silently miss tests.

Runtime jobs keep their test matrices. Unaffected runtime setup/test steps skip,
but their jobs still finish successfully. An always-running `samples-ci` job
requires the planner and every runtime job to succeed; failures, cancellations
or unexpected job skips fail it. This is the stable required branch check.
Adding a new runtime requires registering its job as a dependency of this gate
and extending the planner/runner, not changing repository branch rules.

Workflow edits run all tests. Do not add top-level path filters that prevent the
required gate from appearing. Pin action revisions and let Dependabot maintain
them. Branch review policy is independent of CI; its temporary setup exception
must not be changed by a source-layout migration.

## Moving a published sample

Update its catalog path, sample README, root index, CI and any fixture paths.
Update links and clone/run commands in the developer portal in coordinated PRs.
Publish the new source path before merging portal changes that reference it.
The samples repository PR must link its companion docs PRs, and those PRs must
state the publication dependency. Do not leave duplicate implementations at old
paths. Older Git revisions remain available for readers needing a prior layout.

Run catalog/planner tests and every moved sample's offline suite before review.
CI verifies supported runtime versions. A live Sandbox exercise is separate and
must not become a default test step.

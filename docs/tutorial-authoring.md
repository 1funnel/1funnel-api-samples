# Authoring a complete application tutorial

A **guide** explains how to perform a specific API task, with options and request
examples. A **tutorial** teaches by walking a developer through a working
application from setup to a saved outcome, including recovery. The API reference
is authoritative for exact fields, errors and operations. Smaller request
examples remain welcome; do not present them as complete application tutorials.

## Propose and submit

1. Open a sample/tutorial proposal with the task, audience, language, runtime,
   prerequisites, expected result and related existing examples.
2. Add or improve a runnable sample following [structure.md](structure.md).
   Include source, tests, placeholder configuration, README, catalog entry and
   runtime CI. Run the offline tests before review.
3. Put the full walkthrough in `tutorial.md` alongside that sample's README.
   The README remains the concise run/test reference; the tutorial explains the
   complete learning sequence. Do not duplicate application source into prose
   when a focused excerpt and source link suffice.
4. Open a PR linking the proposal, sample, tutorial draft and test results.
   Report any live Sandbox exercise separately. No live SMS or real credentials
   belong in default tests, fixtures or public review material.

You can submit Markdown and runnable source entirely through this public repo;
you do not need access to the private portal source. For portal-only wording
fixes, open a documentation issue with the page URL and proposed replacement.
For small sample/README fixes, a direct PR with reproduction and tests is enough.

## Walkthrough outline

- **Outcome and audience:** what the developer will build and observe, with the
  runtime and required experience stated up front.
- **Prerequisites:** approved API access, issued business ID, runtimes and any
  permitted sender/recipient or template. Describe available capabilities in
  developer-facing terms; do not teach internal IAM administration.
- **Offline start:** exact clone, directory and test commands that work in a
  fresh checkout without credentials or other language runtimes unless stated.
- **Configuration:** placeholder environment values, how configuration loads,
  and any persistent local storage. Never include an actual token, key or code.
- **Build and run:** ordered steps linking to the tested source and canonical
  API operations. Name exact expected HTTP success statuses. Distinguish
  asynchronous acceptance from eventual delivery or processing results.
- **Observe the result:** show which IDs/status/timestamps are saved and how the
  developer inspects them. Correlate resources with the correct application user
  or session; do not substitute a hardcoded example ID for a returned resource ID.
- **Recover:** demonstrate the task's relevant failure paths, such as uncertain
  acceptance, duplicate/reordered events, expired OTPs or a failed lookup.
- **Operational boundary:** explain what must be reviewed before production,
  including scheduling, storage, retries and application-specific authorization.
- **Next steps:** point to related guides/reference and contribution routes.

Use one language per application tutorial when that keeps the sequence runnable.
Link to the portal's multi-language request guides rather than claiming every
language has the same application coverage. Do not imply an official SDK exists.

## Review and publication

Maintainers review the proposal/PR for contract correctness, reproducibility,
clarity, failure handling and sensitive-data exposure. Revisions may be required.
Acceptance does not promise a release date or automatically publish the draft in
the portal. Maintainers prepare a separate portal change for approved material,
arrange review and link the publication PR or resulting page back to the public
contribution. Keep code paths and portal instructions synchronized.

Contributions use Apache-2.0. Request attribution in the PR if desired; avoid
private contact details in the draft. The portal and repository are maintained
separately, so use issues to track publication rather than assuming synchronization.

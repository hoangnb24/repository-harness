# Design

## Replay Fixtures

Use v1 and v2 semantic operations to materialize a legacy link, precise link,
pre-link trace, and post-link trace into two fresh repositories. Compare
completion proof and closure results.

## Validator Contract

Expose the changeset directory as a test-only-compatible environment override.
Default execution builds the workspace CLI; explicit `HARNESS_CLI` remains an
operator-owned override. A shell regression copies the repository changesets,
appends later/corrupt proof operations, and checks selection and validation.

## Timestamp Invariant

Passing proof requires `YYYY-MM-DD HH:MM:SS` whose SQLite round trip is exact.
The rule applies uniformly to US-073 through US-084.

## Trace Integrity

Historical trace rows remain append-only. US-084 records a new detailed trace
using comma-separated CLI values and an omitted empty errors option.

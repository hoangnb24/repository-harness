# US-030 Changeset Apply

## Status

implemented

## Lane

normal

## Product Contract

`harness-cli` must be able to apply a committed changeset through semantic
operations, not direct SQLite diffing.

## Relevant Product Docs

- `docs/HARNESS.md`
- `docs/TOOL_REGISTRY.md`

## Acceptance Criteria

- A command exists to apply one changeset file.
- Applying a changeset is idempotent: replaying an already applied changeset is
  a no-op.
- Each changeset is applied in a single database transaction.
- Failure reports the failing operation and leaves the database unchanged.
- The database records applied changeset ids for future sync/rebuild behavior.

## Design Notes

- Suggested command: `harness-cli db changeset apply <path>`.
- Tables: likely add `changeset_applied`.
- Domain rule: apply operations through repository methods or equivalent
  command handlers, not ad hoc SQL patches.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-030 --unit 1 --integration 1 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Operation replay tests, duplicate replay tests, and failure rollback tests. |
| Integration | Apply a fixture changeset into an empty temp DB and query expected rows. |
| E2E | Re-run apply and prove state is unchanged. |
| Platform | CLI smoke for success, duplicate, and malformed changeset cases. |
| Release | `cargo test --workspace`; `cargo fmt --check`; `cargo clippy --workspace -- -D warnings`. |

## Harness Delta

This is the core replay primitive that external orchestrators will call.

## Evidence

- `scripts/schema/006-changeset-applied.sql` adds `changeset_applied`.
- `cargo test --workspace` passed with changeset apply/idempotence coverage.
- CLI smoke applied a generated changeset into a separate temp database,
  replayed the same changeset as a no-op, and verified the target matrix row.
- CLI rollback smoke with an unsupported operation exited non-zero and left
  both `story` and `changeset_applied` counts at `0`.

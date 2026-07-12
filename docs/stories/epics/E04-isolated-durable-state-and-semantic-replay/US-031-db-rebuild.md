# US-031 Database Rebuild From Changesets

## Status

implemented

## Lane

normal

## Product Contract

A clone with no `harness.db` must be able to reconstruct durable Harness state
from committed changesets.

## Relevant Product Docs

- `docs/HARNESS.md`
- `docs/HARNESS.md`

## Acceptance Criteria

- `harness-cli db rebuild --from .harness/changesets` creates a fresh database.
- Rebuild applies changesets in deterministic order.
- Rebuild fails loudly on malformed or incompatible changesets.
- Rebuild does not require any external orchestrator runtime state.
- Rebuilt DB can pass `query matrix`, `query decisions`, `query traces`, and
  `audit`.

## Design Notes

- Commands: `db rebuild`.
- Inputs: committed `.harness/changesets/*.changeset.jsonl`.
- Domain rule: `harness.db` is a local index over committed changesets.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-031 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Ordering and rebuild-path tests. |
| Integration | Rebuild from fixture changesets and query records. |
| E2E | Remove a temp DB, rebuild, then run representative query/audit commands. |
| Platform | macOS/Linux shell smoke with relative and absolute changeset paths. |
| Release | `cargo test --workspace`; `cargo fmt --check`; `cargo clippy --workspace -- -D warnings`. |

## Harness Delta

Completes the v0 prerequisite that makes local DB state disposable.

## Evidence

- `harness-cli db rebuild --from <dir>` implemented for fresh databases.
- `cargo test --workspace` passed with rebuild success and existing-DB refusal
  coverage.
- CLI smoke generated a changeset in one temp repo, rebuilt a fresh DB in a
  second temp repo, and verified the rebuilt matrix row.
- CLI smoke confirmed a second rebuild against an existing DB exits non-zero
  with an actionable message.

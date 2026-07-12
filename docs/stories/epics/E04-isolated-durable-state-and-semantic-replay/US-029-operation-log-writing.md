# US-029 Semantic Operation Log Writing

## Status

implemented

## Lane

normal

## Product Contract

When `HARNESS_RUN_ID` is set, every durable write performed by `harness-cli`
must append a matching semantic operation to
`.harness/changesets/<run_id>.changeset.jsonl` in the active workspace.

## Relevant Product Docs

- `docs/HARNESS.md`
- `docs/HARNESS.md`
- `docs/TRACE_SPEC.md`

## Acceptance Criteria

- A changeset starts with a single `changeset.header` operation containing
  version, run id, and base schema version.
- Durable write commands append stable semantic operations, not SQLite diffs.
- The log append is transactionally paired with the database write: either both
  happen or neither happens.
- At minimum, operations exist for intake, story add/update, decision add,
  backlog add/close, intervention add, trace add, tool register/remove/check,
  and verification result writes.
- Running without `HARNESS_RUN_ID` preserves current behavior and writes no
  changeset.

## Design Notes

- Commands: durable write commands only.
- Tables: no schema change required unless applied changeset tracking is pulled
  into this story.
- Domain rules: operation payloads should be schema-versioned, stable, ordered,
  and replayable.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-029 --unit 1 --integration 1 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Operation serialization tests for every supported operation type. |
| Integration | Temp DB plus `HARNESS_RUN_ID` smoke verifies DB row and JSONL operation are both written. |
| E2E | n/a for this CLI-only capability. |
| Platform | Verify relative `.harness/changesets/` path resolves from repo root on macOS/Linux. |
| Release | `cargo test --workspace`; `cargo fmt --check`; `cargo clippy --workspace -- -D warnings`. |

## Harness Delta

This turns committed changesets into the future durable source of truth.

## Evidence

- `cargo test --workspace` passed: 32 tests.
- `cargo fmt --check` passed.
- `cargo clippy --workspace -- -D warnings` passed.
- Rebuilt local `scripts/bin/harness-cli` from `target/release/harness-cli`.
- Unit tests cover changeset header/operation writing and failed transaction
  rollback with no DB row and no changeset file.
- CLI smoke with `HARNESS_RUN_ID=run_smoke` produced `changeset.header`,
  `intake.add`, `story.add`, and `story.update` operations.
- Required-operations CLI smoke produced all required operation types:
  `intake.add`, `story.add`, `story.update`, `story.verify`, `decision.add`,
  `decision.verify`, `backlog.add`, `backlog.close`, `tool.register`,
  `tool.check`, `tool.remove`, `trace.add`, and `intervention.add`.
- CLI smoke without `HARNESS_RUN_ID` left `.harness/changesets/` absent.

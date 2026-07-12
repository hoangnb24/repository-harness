# US-073 Story Dependency Mutation And Replay

## Status

planned

## Lane

normal

## Product Contract

Humans and agents can create, inspect, and remove Harness story dependency edges
through the Rust CLI, and those edges survive semantic changeset apply and fresh
database rebuild. This capability is required before downstream E09 stories are
made runnable on the generic work board.

## Relevant Product Docs

- `docs/stories/epics/E09-self-improving-harness-lifecycle/README.md`
- `docs/contracts/harness-orchestration-v1.md`
- `docs/contracts/harness-orchestration-v1.md`
- `docs/TOOL_REGISTRY.md`
- `scripts/schema/007-story-dependencies.sql`

## Dependencies

- Blocked by: none.
- Blocks: `US-074`.
- Planning responsibility: after the command exists, register `US-074` through
  `US-080` and the E09 dependency edges in one replayable changeset.

## Acceptance Criteria

- The CLI exposes `story dependency add --blocker <id> --blocked <id>`,
  `story dependency remove --blocker <id> --blocked <id>`, and
  `query dependencies [--story <id>]`.
- Adding an edge validates both stories, rejects self-dependency, is idempotent,
  and rejects a dependency cycle without partial writes.
- Removing a missing edge exits successfully, reports `unchanged`, writes no
  semantic operation, and is covered by command-contract tests.
- Dependency writes use `with_logged_write` when `HARNESS_RUN_ID` is set.
- Semantic operations for dependency add/remove apply idempotently and survive
  `db rebuild`.
- generic work board derivation sees blocked and ready states from CLI-authored
  dependency rows.
- CLI help and `docs/TOOL_REGISTRY.md` describe the new capability.
- The implementation registers durable rows for `US-074` through `US-080` and
  the exact E09 graph from the epic README; after sync, only unblocked E09 work
  appears Ready.

## Design Notes

- Commands: `story dependency add --blocker <id> --blocked <id>`,
  `story dependency remove --blocker <id> --blocked <id>`, and
  `query dependencies [--story <id>]`.
- Queries: direct blocker and blocked relationships with deterministic ordering.
- API: Rust CLI only; no application API change.
- Tables: existing `story_dependency`; no schema redesign.
- Domain rules: an edge means `blocker -> blocked`; cycles are invalid planning
  state and must be rejected before write.
- Changesets: add versioned `story.dependency.add` and
  `story.dependency.remove` operations.
- UI surfaces: existing generic work board consumes the resulting table; no UI code
  change is required unless a test exposes a board integration defect.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-073 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Typed command parsing, missing story, self-edge, duplicate edge, cycle detection, remove behavior, and deterministic query ordering. |
| Integration | Temporary database exercises add/query/remove and proves transaction rollback on invalid cycles. |
| E2E | E09 fixture shows `US-074` Ready and later stories Blocked according to the documented graph. |
| Platform | Semantic changeset apply and `scripts/validate-changeset-rebuild.sh` preserve every E09 edge. |
| Release | Workspace fmt/test/clippy and CLI help checks pass. |

Planned story verification:

```bash
sh -c 'cargo test -p harness-cli -- --list | rg "story_dependency_command" && cargo test -p harness-cli story_dependency_command -- --nocapture && scripts/validate-changeset-rebuild.sh'
```

## Harness Delta

This story removes the current raw-SQL planning gap. Future epic dependency
graphs can become board-visible and replay-safe through the supported CLI.

## Non-Goals

- Do not add a durable epic row or story hierarchy behavior.
- Do not change external orchestrators scheduling beyond consuming the existing dependency
  table.
- Do not implement proposal lifecycle behavior in this story.

## Evidence

- Current local intake: `#177`; the canonical intake operation is in planning
  run `run_1783670632_e09_planning`, because numeric ids remap on rebuild.
- Planning discovery: `story_dependency` exists and external orchestrators read it, but the
  current CLI and semantic changeset applier have no supported mutation path.

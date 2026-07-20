# US-114 Define Reproducible Core State Epic

## Status

implemented

## Lane

normal

## Product Contract

Define a lean, dependency-ordered epic that makes the Harness source control
plane reconstructable from Git without committing its writable database or
adding task lifecycle ceremony.

## Relevant Product Docs

- `docs/stories/epics/E15-reproducible-core-state/README.md`
- `docs/FEATURE_INTAKE.md`
- `docs/CONTEXT_RULES.md`
- `docs/decisions/0004-sqlite-durable-layer.md`
- `docs/stories/epics/E04-isolated-durable-state-and-semantic-replay/README.md`

## Acceptance Criteria

- The epic explains the current failure as a concrete cause-and-effect chain.
- It defines the snapshot, automatic JSONL capture, worktree-local database,
  revision-conflict, agent-recovery, and CI proof responsibilities.
- It compares credible paths and records why capture and guards precede snapshot
  activation.
- It separates business priority from dependency-safe execution order using
  Now, Next, and Later horizons.
- It defines measurable exit criteria, non-goals, stop conditions, and
  reconciliation triggers.
- Only this planning story is registered; implementation stories remain behind
  an explicit execution boundary.

## Design Notes

- Reuse the existing typed changeset envelope and semantic replay foundation.
- Keep normal CLI commands as the only common-path operator interface.
- Treat source tracked-state mode separately from installed consumer behavior.
- Let agents resolve semantic conflicts after Harness reports them; do not add
  automatic reconciliation machinery in this epic.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Not applicable to this planning-only story. |
| Integration | Not applicable to this planning-only story. |
| E2E | Document contract check confirms the epic, story, final reserved id, and execution boundary exist. |
| Platform | Not applicable to this planning-only story. |
| Release | Not applicable; no product implementation or release is authorized. |

## Harness Delta

- Intake `#222` records the planning request.
- `US-114` is the only runnable story added.
- One semantic changeset records intake, story lifecycle, and completion trace.
- No schema, CLI, bootstrap, or snapshot behavior changes in this story.

## Evidence

- `test -f docs/stories/epics/E15-reproducible-core-state/README.md`
- `test -f docs/stories/epics/E15-reproducible-core-state/US-114-define-reproducible-core-state-epic.md`
- `rg -q 'US-119' docs/stories/epics/E15-reproducible-core-state/README.md`
- `rg -q 'Execution boundary' docs/stories/epics/E15-reproducible-core-state/README.md`
- `tests/docs/test-doc-contracts.sh`
- `git diff --check`

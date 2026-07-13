# Overview

## Status

in progress

## Current Behavior

Harness has strong proof, replay, and snapshot primitives, but several public
paths can bypass the invariants described by its documentation. Generic status
updates can implement stories without proof; arbitrary SQL can write through a
query command; ignored local runtime artifacts can drift from checked-out
source; and the default agent bootstrap retrieves far more context than its own
lane budgets allow.

## Target Behavior

- Only `story complete` can transition active work to `implemented`, and it
  continues to require fresh passing proof.
- Every command classified as a query is physically unable to mutate SQLite.
- Agents can cheaply detect CLI-version and database-schema drift before
  trusting task-state output.
- Default matrix output can be reduced to the active or relevant work set.
- Answer, review, diagnose, and plan requests remain read-only; implementation
  logging applies to change/build/fix work.
- Root, Bash, PowerShell, and Claude instruction surfaces share one tested
  context policy.
- Pull requests run contract, documentation, and representative task checks
  before merge.

## Affected Users

- Agents and humans using Harness to decide what work is runnable or complete.
- Maintainers developing the Harness CLI from a source checkout.
- External orchestrators consuming protocol-v1 story and work-graph commands.
- Projects installing or refreshing Harness on macOS, Linux, or Windows.

## Affected Product Docs

- `AGENTS.md`
- `CLAUDE.md`
- `docs/HARNESS.md`
- `docs/CONTEXT_RULES.md`
- `docs/HARNESS_AUDIT.md`
- `docs/HARNESS_MATURITY.md`
- `docs/TOOL_REGISTRY.md`
- `docs/contracts/harness-orchestration-v1.md`
- `scripts/README.md`

## Non-Goals

- Change the meaning of historical imported or replayed `implemented` records.
- Remove explicit administrative migrations or semantic changeset replay.
- Add a bundled coding-agent runtime, UI driver, or observability stack.
- Make breaking protocol-v1 response-shape changes.

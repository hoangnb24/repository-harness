# E05 Symphony Local Runner

## Goal

Build the first useful `harness-symphony` workbench: doctor, work discovery,
isolated preparation, run contract, result validation, and local run status.

## Product Contract

Humans and agents can start from a Harness story and get an isolated workspace
with a copied database, explicit run contract, required outputs, and local
status without mutating root durable state.

## Stories

1. `US-032` - Symphony crate and configuration loading.
2. `US-033` - `harness-symphony doctor`.
3. `US-034` - Work list.
4. `US-035` - Run state store and single active-run lock.
5. `US-036` - Prepare isolated run worktree.
6. `US-037` - Run contract and worktree `AGENTS.md` shim.
7. `US-038` - Result validation and custom command adapter.
8. `US-039` - Runs list/show and status.

## Exit Criteria

- `harness-symphony run <story-id> --prepare-only` satisfies the MVP acceptance
  criteria in `docs/SYMPHONY_SCOPE.md`.
- A completed local run is accepted only when summary, result, validation
  evidence, and forbidden-path checks pass.
- Local status tells the next human action.

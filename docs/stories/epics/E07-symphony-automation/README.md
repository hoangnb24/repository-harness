# E07 Symphony Automation

## Goal

Add automation only after the local Symphony workbench and review/sync loop are
trusted.

## Product Contract

Automation must reuse the same run contracts, result files, workspace
isolation, changesets, and sync semantics proven in v1/v2.

## Stories

1. `US-044` - Tiny-lane lightweight run path.
2. `US-045` - Auto-mode queue and work-source adapters.

## Exit Criteria

- Tiny stories can run with reduced worktree ceremony while keeping database
  isolation and result artifacts.
- Queue and external work-source adapters exist only after single-run isolation
  is stable.

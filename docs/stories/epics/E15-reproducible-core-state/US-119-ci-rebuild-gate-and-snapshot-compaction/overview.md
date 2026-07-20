# US-119 CI Rebuild Gate And Snapshot Compaction

## Story

As a Harness maintainer, I want every pull request to prove a missing-database
bootstrap from tracked state and want a guarded maintenance command for rare
snapshot replacement, so reproducibility cannot silently regress or grow
without bound.

## Acceptance Criteria

- Linux CI asserts `harness.db` is absent after checkout, bootstraps from tracked
  state, and runs the repository contract and durable-table parity gate.
- Windows CI asserts the same missing starting state and exercises PowerShell
  materialization before installer validation.
- Snapshot replacement is explicit, verifies the existing tuple, requires the
  caller's expected current logical hash, verifies the candidate before
  activation, and restores the prior tuple on an in-process failure.
- A stale replacement precondition changes neither tracked file.
- The replacement procedure is documented as optional maintenance, never a
  normal task step.
- A final fresh tracked-state rebuild satisfies every E15 exit criterion.

## Non-Goals

- Scheduled or automatic compaction.
- Deleting historical JSONL during this epic.
- Rewriting shared changesets.

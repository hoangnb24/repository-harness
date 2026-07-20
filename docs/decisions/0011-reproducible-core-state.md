# 0011 Reproducible Core State

Date: 2026-07-20

## Status

Accepted

## Context

The Harness source repository stores its writable control-plane state in an
ignored SQLite database. Semantic JSONL changesets exist, but callers must set
`HARNESS_RUN_ID`; a normal successful mutation can therefore exist only in one
maintainer's database. A fresh clone cannot reconstruct that state, while
tracking the writable SQLite file would create binary worktree conflicts.

The decision is repo-local and affects the Harness CLI, source bootstrap,
SQLite state, semantic changesets, and CI. Installed consumer repositories must
keep their current local operational-state behavior.

## Decision

The authoritative reproducible inputs for the Harness source control plane are:

1. a committed, verified, read-only SQLite baseline snapshot; and
2. committed semantic JSONL changesets created after that baseline.

Each source worktree materializes its own ignored writable `harness.db` from
those inputs. When a normal typed mutation targets the default database in a
Harness CLI source checkout, the mutating CLI process automatically creates one
uniquely named changeset if the caller did not provide `HARNESS_RUN_ID`.

Mutable-entity operations use expected revisions. Replay stops and reports a
stale revision instead of choosing a winner. An agent investigates, rebases,
and reruns the normal high-level command; Harness does not add an automatic
semantic merge engine. Snapshot replacement is an explicit maintenance action,
not part of ordinary task execution.

## Alternatives Considered

1. **Track the writable SQLite file.** Rejected because binary merges, WAL
   artifacts, and unrelated write churn make worktrees unreliable.
2. **Use changesets without a baseline.** Rejected because the current core
   state is not fully represented by the small tracked replay set, and replay
   time grows without a bounded starting point.
3. **Publish the baseline before automatic capture and revision guards.**
   Rejected because it preserves a mutation-loss window and last-writer-wins
   replay during the cutover.
4. **Replace SQLite with a full event-sourcing system.** Rejected because the
   existing typed changeset and snapshot primitives cover the required outcome
   with much less operational ceremony.

## Consequences

Positive:

- A fresh clone and independent worktrees can reconstruct the same core state.
- Normal source mutations become Git-visible without extra lifecycle commands.
- Conflicting intent is surfaced before state is silently overwritten.
- SQLite remains the fast local query and transaction engine.

Tradeoffs:

- The source repository carries a reviewed binary baseline artifact.
- Changeset format and schema revisions require compatibility tests.
- Git conflicts in generated changesets still require agent judgment when both
  branches intentionally changed the same entity.
- Snapshot publication must exclude secrets, machine paths, and product-owned
  state.

## Follow-Up

- `US-115` through `US-119` implement and verify this decision.
- Update decision `0004` documentation after materialization becomes active.
- Replace the baseline only through the verified compare-and-swap maintenance
  procedure; ordinary tasks append JSONL and never compact.

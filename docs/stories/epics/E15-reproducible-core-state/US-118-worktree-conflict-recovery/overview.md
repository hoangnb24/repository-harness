# US-118 Worktree Conflict Recovery

## Story

As an agent working in a Git worktree, I want independent Harness changes to
converge and stale same-entity changes to stop with enough context to rebase my
intent, without a separate reconciliation subsystem.

## Acceptance Criteria

- Two real Git worktrees update different entities and their JSONL files merge
  and replay successfully in either branch-integration sequence.
- Two worktrees update the same revision; Git can merge the separate files, but
  Harness replay rejects the stale operation with changeset, entity, expected,
  and actual revision.
- The failed changeset has no partial effects.
- Recovery removes only the agent-owned stale file, rebuilds from merged state,
  and reruns the ordinary high-level command to produce a fresh guarded intent.
- No automatic resolver selects product intent. Ambiguity is escalated to the
  user rather than hidden in database surgery.

## Scope

This story proves and documents the recovery loop. It does not introduce locks,
an event DAG, merge drivers, or automatic semantic conflict resolution.

# Exec Plan

## Goal

Turn same-entity worktree races into deterministic, actionable replay conflicts
without blocking independent mutations.

## Scope

In scope:

- Additive revision migration and trigger/update semantics.
- Revision-bearing mutable operations.
- Backward-compatible replay.
- Human and machine conflict diagnostics.
- Same-entity, independent-entity, rollback, and legacy-operation tests.

Out of scope:

- Automated conflict resolution or branch rewriting.
- Snapshot activation and worktree orchestration.

## Risk Classification

Risk flags:

- Data model.
- Existing behavior.
- Public contracts.
- Weak proof around concurrent worktrees.

Hard gates:

- Schema migration and durable replay compatibility.

## Work Phases

1. Add migration `014` and schema coherence expectations.
2. Add revision conflict domain error and protocol mapping.
3. Emit guarded operations for mutable entity writes.
4. Enforce guarded replay while accepting legacy versions.
5. Prove independent and conflicting changesets transactionally.
6. Run rebuild, workspace, documentation, and installer proof.

## Stop Conditions

Pause if:

- historical changesets can no longer rebuild;
- independent entity mutations require a shared revision;
- replay can partially commit before detecting a conflict; or
- resolution requires automatically selecting product intent.


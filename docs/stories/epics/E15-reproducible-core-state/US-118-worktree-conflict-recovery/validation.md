# Validation

## Command

```text
tests/worktrees/test-core-state-conflict-recovery.sh
tests/docs/test-doc-contracts.sh
git diff --check
```

## Required Evidence

- Real `git worktree` branch commits and merges.
- Independent entity values and revisions after replay.
- Conflict envelope with run and revision details.
- Unchanged value after failed stale replay.
- Rebased high-level operation with the current expected revision.

## Acceptance Evidence

- `tests/worktrees/test-core-state-conflict-recovery.sh` creates four real Git
  worktrees, commits and merges independent and colliding JSONL files, and
  rebuilds from the merged tracked state.
- Independent updates finish at `WT-A revision 1` and `WT-B revision 1`.
- The second same-entity file returns exit `3`, code `CONFLICT`, entity
  `story/WT-A`, expected revision `1`, and actual revision `2`; its apply marker
  and value are absent after rollback.
- The agent recovery drops only the local stale file, rebuilds, and reruns
  `story update`, which emits expected revision `2` and converges at revision
  `3` without hand-authored replacement JSONL.
- Documentation and installer-manifest validation pass with
  `docs/WORKTREE_CONFLICTS.md` included.

# Harness Worktree Conflicts

Each worktree owns an ignored writable `harness.db`. Git shares only the
verified baseline, manifest, and typed JSONL changesets.

Independent changes normally need no special handling: merge their unique
changeset files and bootstrap or materialize again. Per-entity revision guards
allow both operations when they observed different entities.

If replay reports `CONFLICT`, use this loop:

1. Read the named changeset, entity id, expected revision, and actual revision.
2. Inspect the current entity and both intents.
3. If your unmerged intent is unambiguous, remove only your stale generated
   changeset from your branch.
4. Rebuild or materialize the worktree database from the merged tracked state.
5. Rerun the normal command such as `story update`; do not hand-author a
   replacement JSONL operation.
6. Run the story proof and commit the newly generated changeset.

Ask the user when the correct intent is ambiguous, when resolution would weaken
a gate, or when the stale file is already shared history. Harness detects the
collision; it does not decide which product intent should win.

# Execution Plan

1. Create a disposable Git repository with a seed changeset and two attached
   worktrees.
2. Generate independent guarded updates from identical databases, commit and
   merge their unique files, and replay to convergence.
3. Generate two same-story updates from the same revision and merge both files.
4. Assert structured conflict output and transaction rollback.
5. Exercise the documented agent recovery by replacing only the stale owned
   intent with a high-level command generated against current merged state.
6. Add the fixture to pre-merge validation and record proof.

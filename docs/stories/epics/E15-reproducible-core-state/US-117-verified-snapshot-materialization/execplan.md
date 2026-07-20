# Execution Plan

1. Add portable snapshot verification/materialization scripts.
2. Route only missing default source databases through materialization.
3. Add positive and tamper/atomicity fixtures for Bash and the PowerShell
   contract.
4. Resolve the existing core-epoch backlog occurrence through the typed CLI.
5. Publish the initial snapshot and manifest from the ownership-clean live
   database.
6. Rebuild a disposable database, compare logical state, run the full suite,
   and record story proof.

## Rollback

Before merge, remove the untracked baseline tuple and revert bootstrap routing.
After merge, restore a previous reviewed snapshot and manifest together; never
mix one file from two snapshot generations.

## Stop Conditions

- Ownership or sensitive-data scan fails.
- Included changeset identity cannot be bound to exact bytes.
- Replayed logical state differs from the live source state.
- Consumer bootstrap behavior changes.

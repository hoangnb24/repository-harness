# E04 Isolated Durable State And Semantic Replay

## Goal

Make `harness-cli` safe for isolated repository workflows before any runner code exists.

## Product Contract

`harness-cli` must be able to operate against a copied database and append a
semantic changeset while it mutates durable state. The root `harness.db` must
not be touched during isolated runs.

## Stories

1. `US-028` - `HARNESS_DB_PATH` database override.
2. `US-029` - Semantic operation log writing.
3. `US-030` - Changeset apply and idempotent replay.
4. `US-031` - Database rebuild from committed changesets.

## Exit Criteria

- `HARNESS_DB_PATH` is the preferred database override, with legacy `HARNESS_DB`
  behavior preserved where practical.
- Every durable write path used by Harness stories records a semantic operation
  when `HARNESS_RUN_ID` is set.
- Changesets can be applied repeatedly without duplicating state.
- A fresh `harness.db` can be rebuilt from `.harness/changesets/`.

# Design

## Domain Model

- Semantic operations carry authoritative event timestamps and link-order
  boundaries instead of deriving them during replay.
- Resolver links capture the stable trace count visible before the mutation;
  completion requires a later uid-bearing trace, eliminating same-second
  ambiguity.
- Audit decisions require stable recorded audit episodes.
- Rejection reasons compare exact structured values.

## Application Flow

1. Record live timestamps and boundaries inside the same write transaction.
2. Append them to semantic changesets.
3. Replay exact values.
4. Exercise each prior failure through a focused test.
5. Compare live and rebuilt lifecycle/audit state.

## Interface Contract

- `--outcome-due` accepts valid RFC3339 timestamps for `Z`, positive offsets,
  and negative offsets.
- Invalid or stale audit decisions remain actionable errors.
- Lightweight Symphony copies enter `in_progress` before execution.

## Data Model

- Add a migration for resolver-link trace baselines and structured proposal
  rejection reasons where needed.
- Preserve compatibility with existing migrations and replay operations.
- Backfill old resolver links conservatively; no historical proof is invented.

## UI / Platform Impact

No new UI. Symphony isolated and lightweight execution must share the same
copied-story lifecycle state.

## Observability

The review ledger records per-finding closure evidence. Rebuild validation
checks story proof and audit entropy, not only row presence.

## Alternatives Considered

1. Higher-resolution timestamps alone. Rejected because replay and cross-process
   ties still need a deterministic order boundary.
2. Leaving baseline defects open because they predate the branch. Rejected
   because the explicit goal is to complete every item in the ledger.

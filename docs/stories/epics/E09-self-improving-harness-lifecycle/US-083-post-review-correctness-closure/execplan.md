# Exec Plan

## Goal

Close F-014 through F-017 with regression proof and live/rebuild parity.

## Risk Classification

High-risk: database migration, semantic replay behavior, existing lifecycle
behavior, and validation integrity.

## Phases

1. Add mixed resolver-order and v11 migration parity fixtures.
2. Correct the completion boundary query and migration backfill.
3. Make rebuild validation executable-explicit and proof-update-safe.
4. Run focused and workspace validation plus fresh rebuild/audit parity.
5. close US-083 and update the review resolution matrix.

## Stop Conditions

Stop if compatibility would require fabricating historical nanosecond order or
discarding existing evidence.

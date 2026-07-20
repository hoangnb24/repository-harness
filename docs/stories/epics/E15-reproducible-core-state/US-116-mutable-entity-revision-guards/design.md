# Design

## Domain Model

`revision` is a non-negative integer on each mutable entity row. Creation starts
at `0`; every update advances it exactly once. A guarded operation contains
`expected_revision`, the value observed in the same SQLite transaction before
the mutation.

## Application Flow

```text
source mutation of entity E
  -> read E.revision = N inside write transaction
  -> apply mutation and advance E.revision to N+1
  -> emit operation(expected_revision=N)

replay operation for E
  -> read actual revision
  -> actual == expected: apply and advance
  -> actual != expected: roll back changeset and report structured conflict
```

## Interface Contract

Human-readable errors name the changeset and entity. Protocol JSON maps revision
mismatch to `CONFLICT` and includes structured details. No conflict-resolution
command is added.

## Data Model

Migration `014` adds `revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0)`
to `story`, `decision`, `backlog`, `tool`, and `audit_evidence_episode`.

New guarded operation versions require `expected_revision`. Older operation
versions retain their legacy replay behavior so historical changesets remain
rebuildable.

## UI / Platform Impact

CLI output and JSON error envelopes change only on stale replay. SQLite integer
and JSON number behavior is platform-independent.

## Observability

Conflict output records changeset run ID, entity kind and ID, expected revision,
and actual revision. It does not record a resolution because no resolution has
yet occurred.

## Alternatives Considered

1. Last-writer-wins replay. Rejected because it silently loses intent.
2. One global database revision. Rejected because independent entity changes
   would conflict unnecessarily.
3. Full field snapshots as preconditions. Rejected because payloads become
   larger and schema evolution makes comparisons fragile.


# US-117 Verified Snapshot Materialization

## Story

As a Harness source contributor, I want a missing worktree database restored
from reviewed tracked inputs so that a clone is usable without copying another
worktree's writable SQLite file.

## Outcome

The repository tracks one read-only, WAL-safe core snapshot and one manifest.
The manifest binds the snapshot's byte and logical hashes and the exact
changesets already represented by it. Source bootstrap verifies that tuple,
copies the snapshot to a temporary writable database, replays only later
changesets, checks ownership, and atomically installs `harness.db`.

Installed consumers retain their existing local initialization behavior.

## Acceptance Criteria

- A source checkout with no `harness.db` materializes from tracked state.
- Snapshot byte hash, logical hash, schema, SQLite integrity, and core ownership
  are checked before activation.
- A changed snapshot, manifest, or compacted changeset fails closed and leaves
  no output database.
- Changesets represented by the snapshot are skipped only when id and SHA-256
  both match; later changesets replay in filename order.
- Materialization is atomic and never overwrites an existing database.
- Consumer bootstrap behavior is unchanged.

## Scope Boundary

This story establishes the initial verified baseline and restore path. It does
not add ordinary-task compaction, automatic conflict resolution, or a shared
writable database.

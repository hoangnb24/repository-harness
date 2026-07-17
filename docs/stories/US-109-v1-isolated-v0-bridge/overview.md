# US-109: Archive-Only V0 Bridge

Status: **in_progress — local Phase 4 candidate implemented; independent acceptance pending**

Decision 0014 supersedes US-109's earlier automatic-conversion design. The
bridge preserves V0 as archive evidence and never imports V0 operational rows
as active V1 state. Phase 5, Phase 7 platform promotion, production signing,
publishing, and Phase 8 remain closed.

## User outcome

1. Stop V0 writers.
2. Run `harness-v0-migrate inspect`, then `archive` to capture DB+WAL+SHM,
   recognized changesets, and provenance under `.harness-v0-archive`.
3. Optionally run `export` for neutral read-only access to V0 history.
4. Run normal `harness install --v0-archive-manifest
   .harness-v0-archive/<archive-id>/archive-manifest.json`.
5. The Phase 3 install transaction initializes fresh V1 from repository files
   and commits a receipt binding the exact archive/export digest.
6. All later writes use `harness`; the V0 archive remains read-only indefinitely.

Concrete example: a task committed only in `harness.db-wal` appears in the
standalone backup and neutral export. It does not appear as an active V1 task.
The V1 manifest instead records which immutable archive/export preserved it.

## Boundaries

- Bridge grammar is exactly `inspect`, `export`, `archive`, `version`.
- There is no bridge `preview`, `apply`, `resume`, `rollback`, conversion
  journal, row mapper, V1 target writer, or bridge-owned rollback state.
- Core remains exactly six commands and contains no SQLite/V0 implementation.
- No command creates `harness-v1.db`.
- Existing `.harness/legacy`, `.harness/recovery`, or unauthenticated
  `.harness-v0-archive` content is foreign and never adopted.
- macOS/Linux exercise descriptor-safe capture. Windows builds and proves
  repository capture exits controlled-unsupported code 5 until Phase 7.

## Acceptance state

The local candidate includes contracts, crate code, temporary-copy fixtures,
workflow structure, and Phase 1–4 verifier updates. This is implementation
evidence, not independent acceptance. US-109 remains `in_progress` until the
separate acceptance authority reviews the exact committed candidate.

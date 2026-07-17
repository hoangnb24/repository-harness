# 0014 Archive-Only V0 To V1 Cutover

Date: 2026-07-17

## Status

Accepted

## Context

The first Phase 4 candidate implemented Decision 0011 as automatic conversion:
the bridge previewed target operations, created a conversion journal, mapped V0
rows and repository files into a V1 manifest, applied target writes, and owned
resume and rollback. That made the temporary bridge a second V1 installer and
recovery engine. It also required the permanent core to understand bridge
journals and converted-state receipts.

V0 operational records are historical evidence, not authoritative V1 task
state. Importing them as active V1 state creates ambiguous ownership and carries
the V0 control-plane model across the boundary that V1 was designed to remove.
The approved cutover can be smaller: freeze V0, preserve it exactly, initialize
V1 normally from repository files, and bind the two epochs by digest.

## Decision

Phase 4 is an archive-only cutover. This decision supersedes the automatic
conversion, target mutation, conversion-journal, resume, rollback, and
row-to-V1 mapping portions of Decision 0011 and the original US-109 design. It
does not rewrite their historical rationale.

The user flow is exact:

1. Stop all V0 writes. Capture `harness.db`, existing WAL and SHM, every
   recognized changeset, and recognized provenance through pinned no-follow
   handles with equal pre/copy/post identity, size, and SHA-256.
2. Recover only the private staged DB+WAL, create a standalone SQLite online
   backup, produce the neutral read-only export, and publish one checksummed
   archive under `.harness-v0-archive/<archive-id>/`.
3. Run the normal six-command V1 core installer with
   `harness install --v0-archive-manifest
   .harness-v0-archive/<archive-id>/archive-manifest.json`.
4. The existing Phase 3 install transaction records a
   `repository-harness-v0-archive-receipt/v1` in the fresh V1 manifest. The
   receipt binds the exact archive-manifest, export, standalone-backup, source,
   and payload digests. Phase 3 preview, journal authentication, manifest-last
   commit, resume, and rollback protect only this ordinary core install.
5. All future Harness writes use `harness`. V0 live files and the preserved
   archive are never imported as active V1 state. The archive remains read-only
   indefinitely and no `harness-v1.db` exists.

The bridge grammar is exactly `inspect`, `export`, `archive`, and `version`.
`inspect` is read-only. `export` creates only a new caller-selected neutral
export and can read either frozen live input or a preserved archive. `archive`
creates only archive custody. The bridge has no `preview`, `apply`, `resume`,
`rollback`, `migrate`, installer dispatch, target operation, V1 manifest write,
or rollback state.

Archive publication is append-only. The bridge creates a fresh unique staging
directory, writes and verifies the complete payload and manifest there, then
uses atomic no-replace rename to a fresh unique final directory. A crash before
rename leaves an unaccepted staging directory. Retry chooses a new staging and
final identity and never overwrites or adopts the abandoned or foreign bytes.

`.harness/legacy` and `.harness/recovery` are never bridge archive destinations.
Any existing content there is unknown and unowned. The reserved
`.harness-v0-archive/` custody root is created atomically when absent and is
reused only when its private root-bound HMAC ownership marker authenticates.

Decision 0012 remains authoritative for the compatibility dates, indefinite
local-archive retention, bridge-asset retention, and Phase 8 gates. Decision
0013 remains authoritative for disjoint release trust, encrypted-by-default
archives, explicit two-flag plaintext risk acceptance, pinned source capture,
WAL-only recovery, and fail-closed paths. References in those decisions to a
completed conversion receipt now mean the core-owned archive receipt described
here; references to bridge target mutation or a bridge conversion journal are
superseded and no new such state is created.

Windows repository capture and publication remain unsupported until Phase 7.
The crate and workflow must compile and expose the four-command grammar on
Windows, then repository commands must take the controlled unsupported exit 5.

## Concrete Cause And Effect

1. A V0 row exists only in `harness.db-wal`.
2. Capture copies DB+WAL through retained handles and leaves SHM forensic-only.
3. SQLite opens only the private staged pair and online backup materializes the
   committed row.
4. Export and archive contain the row, while the live V0 bytes remain unchanged.
5. Core sees only archive checksums; it never links SQLite or parses V0 rows.

1. Archive publication crashes after staging is fsynced but before rename.
2. No final archive directory exists, so no archive is accepted.
3. Retry creates a different staging and final ID.
4. Atomic no-replace publication cannot overwrite the abandoned staging or a
   concurrently prepositioned final path.

1. Core install is interrupted after its authenticated recovery journal exists.
2. The staged candidate manifest already contains the exact archive receipt.
3. `harness install --resume <operation-id>` reauthenticates the normal release,
   archive manifest, and payload before manifest-last commit.
4. The resulting repository is fresh V1 linked to archive evidence; no V0 row
   becomes a V1 role, task, run, trace, decision, or backlog record.

## Alternatives Considered

1. Keep automatic conversion but hide it behind fewer commands. Rejected
   because the target mutation, mapping, journal, and rollback ownership remain.
2. Let the bridge write only the V1 receipt. Rejected because that still makes
   the bridge a target mutator and bypasses the accepted Phase 3 install engine.
3. Store archives under `.harness/legacy`. Rejected because existing legacy or
   recovery content does not prove bridge ownership and collides with V1 tool
   custody.
4. Import V0 task rows after normal install. Rejected because archived history
   is evidence, not active V1 operational state.

## Consequences

Positive:

- The bridge is a read/capture/archive tool, not a second installer.
- Core stays at six commands and remains SQLite/V0-free.
- Phase 3 remains the single V1 mutation and recovery engine.
- Archive crashes and retries have a small append-only ownership model.
- Historical V0 evidence remains readable without becoming V1 authority.

Tradeoffs:

- Users intentionally start fresh V1 operational state; there is no automatic
  continuation of V0 task status.
- Encrypted archive export requires the repository owner's age identity.
- Windows repository capture remains closed until Phase 7.

## Follow-Up

- Replace US-109 implementation and proof with the four-command archive model.
- Keep US-109 `in_progress` until independent acceptance.
- Keep Phase 5, Phase 7 production promotion, production keys, publishing, and
  Phase 8 removal closed.

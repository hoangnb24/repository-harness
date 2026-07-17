# US-109: V1 Isolated V0 Bridge

## Current Behavior

Phases 1 through 3 freeze the V0 compatibility contracts and implement the
permanent six-command V1 core, but no executable conversion bridge exists.
`harness` deliberately rejects `inspect`, `export`, `preview`, `apply`,
`resume`, `rollback`, and `migrate`; it has no SQLite dependency and never
opens V0 state. A V0 repository therefore has no accepted path to produce a
neutral export, retain recovery evidence, or atomically enter
`converted-v1-with-archive` mode.

The frozen Phase 1 bridge grammar and schema 1 through 13 inventory are
contract inputs only. The bridge workflow identity is reserved but absent,
and earlier verifiers correctly require that absence until Phase 4 supplies a
live, separately versioned artifact.

## Target Behavior

Add a repository-local binary named `harness-v0-migrate` with exactly seven
top-level commands: `inspect`, `export`, `preview`, `apply`, `resume`,
`rollback`, and `version`. It is a separate crate and release surface whose
dependency direction is bridge to pure V1 behavior. The permanent core neither
depends on the bridge nor gains SQLite, V0 schemas, V0 changesets, a `migrate`
verb, or bridge dispatch.

The bridge conservatively recognizes a repository-root `harness.db` only when
its `schema_version` is in 1 through 13 and its database shape is compatible
with the frozen schema sequence. Recognized changesets must satisfy the closed
header and operation/version matrix. Unknown `.harness` metadata is reported
as unknown/unowned and preserved byte-for-byte.

Capture is source-immutable. Writers must be quiesced; the bridge pins the
repository root and opens descendants no-follow relative to retained parent
descriptors. Each raw DB, WAL, SHM, recognized changeset, and recognized
provenance file is observed before, during, and after copy through the same
final handle. Identity, size, and SHA-256 must remain equal. SQLite then opens
only private staged DB+WAL, treats staged SHM as forensic-only, and creates a
standalone online-backup snapshot.

Before target mutation, the bridge emits a deterministic
`repository-harness-v0-export/v1` document and creates write-once archive
evidence under `.harness/legacy/v0-conversion/<conversion-id>/`. Encryption to
an age/X25519 recipient is the default. Plaintext requires both the contracted
override and the separate risk acknowledgement. No automated action deletes,
overwrites, truncates, moves, or replaces an archive.

Apply follows the journal states `discovered`, `inspected`, `exported`,
`archived`, `prepared`, `applying`, `committed`, and `completed`. It rechecks
source and compatibility digests, applies only deterministic filesystem
operations, audits the candidate V1 structure, and atomically commits the V1
manifest with its embedded completed receipt last. Resume validates journal
evidence and repeats incomplete work only. Rollback changes only journal-owned
post-images whose digests still match; a human edit causes
`recovery-required`, preservation of all evidence, and refusal to overwrite.

## Concrete Cause And Effect

1. A V0 transaction is committed only in `harness.db-wal`.
2. Capture copies and verifies the same open DB and WAL handles without writing
   them.
3. SQLite recovers the staged pair and online backup produces one standalone
   snapshot containing the committed row.
4. Export reads that snapshot, so the row is retained without checkpointing or
   migrating the source database.

1. Apply writes one target-owned V1 artifact and records its exact post-image.
2. The process stops at the next kill point.
3. A human edits the written artifact before rollback.
4. Its live digest no longer equals the journal post-image, so rollback changes
   nothing, marks recovery required, and preserves the human edit, V0 inputs,
   journal, and archive.

1. A V1 manifest exists beside active V0 artifacts but has no completed
   receipt.
2. The pure core receives only a structural repository-state observation from
   its filesystem boundary; it does not open SQLite or parse changesets.
3. Status reports `mixed-invalid` and core mutation remains blocked until the
   bridge resolves the journal.

## Affected Users

- Repository owners converting a supported V0 checkout during the Decision
  0012 compatibility window.
- Release maintainers retaining and verifying the separate bridge artifact
  set through `2028-06-30T23:59:59Z`.
- Reviewers proving that V0 compatibility did not leak into the permanent V1
  core.

## Affected Product Docs

- `docs/REFACTOR_PLAN.md`
- `docs/TEST_MATRIX.md`
- `docs/stories/US-105-harness-v1-implementation/`
- `docs/decisions/0011-time-bounded-v0-conversion.md`
- `docs/decisions/0012-v0-compatibility-window-and-retention.md`
- `docs/decisions/0013-v1-security-and-v0-capture-contract.md`
- `docs/contracts/v1/` and `release/contracts/v1/`

## Non-Goals

- No new V0 feature, schema, migration, lifecycle behavior, or source write.
- No permanent V1 `migrate` or bridge command.
- No conversion of arbitrary `.harness` metadata or import of V0 task state
  into the V1 manifest.
- No target tool execution, automatic V1-to-V0 downgrade, archive cleanup, PR,
  publish, deployment, production key, or Phase 7 platform promotion.

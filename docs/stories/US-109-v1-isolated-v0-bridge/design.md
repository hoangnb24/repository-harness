# Design

## Boundary And Dependency Direction

`harness-v0-migrate` is a separate workspace package and binary. It owns V0
recognition, `rusqlite`, raw capture, export/archive encoding, and conversion
journals. It may consume pure V1 manifest/domain validation, but
`harness-core` must not depend on the bridge, SQLite, V0 schema SQL, or the V0
changeset grammar.

Mixed-version integration uses a structural observation port: the filesystem
adapter reports whether recognized V0 path signatures and conversion journal
or receipt structures coexist with a manifest. The core uses those booleans to
classify `v0-legacy`, `conversion-in-progress`,
`converted-v1-with-archive`, or `mixed-invalid`; it never queries a V0 table or
parses a changeset. This produces the required status decision without
reversing dependency direction.

## Domain Model

- `SourceIdentity`: repository-root identity plus each retained file identity,
  size, and SHA-256.
- `RecognizedInput`: raw DB/WAL/SHM, closed-grammar changeset, or known V0
  installer provenance; every item has a category and disposition.
- `UnknownMetadata`: a reported, unowned path that is never read as V0 state or
  mutated.
- `V0Export`: deterministic `repository-harness-v0-export/v1` containing source
  schema, stable source/category/payload digests, and dispositions. V0 rows are
  legacy evidence, not V1 task records.
- `ConversionArchive`: immutable custody directory, archive manifest,
  standalone snapshot, raw evidence, export, and encrypted or explicitly
  acknowledged plaintext payload.
- `ConversionJournal`: conversion identity, pinned input/compatibility digests,
  confidentiality decision, exact operations, before/post-image evidence, and
  one enumerated state.
- `ConversionReceipt`: embedded V1 manifest record binding bridge release,
  archive path, export/snapshot/archive digests, confidentiality mode, and
  recipient fingerprints.

The journal transition order is closed:

```text
discovered -> inspected -> exported -> archived -> prepared -> applying
           -> committed -> completed
```

Failure before completion leaves a journal at the last durable state. Evidence
conflict changes it to `recovery-required`; that state is never reported as
success.

## Immutable Recognition And Capture

Recognition requires a regular repository-root `harness.db`, opened read-only
and no-follow, with schema version 1 through 13 and no unsupported schema
objects. Changesets are UTF-8 JSON Lines: first nonblank line is the version-1
header, operation versions are 1 or 2 (missing means 1), and every operation is
in the frozen matrix. Duplicate members, malformed lines, unknown operations,
or unsupported versions fail closed. Arbitrary `.harness` entries remain
unknown/unowned.

On Unix, one open repository-root descriptor anchors traversal. Each component
is opened relative to its retained parent with no-follow semantics. The bridge
keeps final handles open, reads `(identity, size, SHA-256)`, rewinds and copies
through the same handle while hashing, then rewinds and hashes again. It
revalidates component identity through the parent after copy. Any link,
replacement, ancestor swap, size drift, or byte drift stops before target
mutation. Source files are never opened writable.

Staging contains private copies of raw DB, WAL, and SHM. Before SQLite opens the
staged database, staged SHM is moved out of the recovery pair inside staging
and retained only as raw archive evidence. SQLite uses read-only source plus
its online-backup API to make a standalone snapshot. Export reads only the
standalone snapshot. Unsupported platforms fail closed at this descriptor
boundary; five-platform parity remains Phase 7 evidence.

Writer quiescence is proven by an exclusive repository-local bridge lock plus
stable DB/WAL identity/size/digest observations. A changing or independently
locked V0 writer makes capture fail rather than producing mixed-time evidence.

## Export And Archive

Export ordering is stable by source identifier and category. JSON uses closed
objects and deterministic member/array ordering; SHA-256 is calculated over
the exact emitted UTF-8 bytes. SQLite values are encoded without inference as
typed neutral payloads so task rows cannot become V1 lifecycle fields.

The archive path is
`.harness/legacy/v0-conversion/<conversion-id>/`. Creation uses no-replace
semantics. Existing exact evidence may be revalidated for idempotent resume,
but no archive byte is opened for truncation or replacement. Default output is
an age/X25519 encrypted payload for the supplied repository-owner recipient;
the manifest records recipient fingerprints and ciphertext digest. Plaintext
is accepted only when both `--archive-plaintext` and
`--acknowledge-plaintext-recovery-risk` are present, and both manifest and
receipt record the override.

## Preview, Apply, And Commit

Preview performs recognition and deterministic planning without mutation. Its
SHA-256 covers the exact public operation projection. Apply requires
`--non-interactive` plus the accepted preview digest, redoes compatibility and
source checks, creates export/archive/journal evidence, and then processes each
operation once.

Each operation records safe repository-relative path, before digest or
absence, exact intended after digest, and completion evidence. A preexisting
different image is a conflict. The candidate manifest adopts useful existing
documents as target-owned `v0-adopted` roles and contains no V0 operational
records. The bridge audits that candidate with pure V1 validation. It writes
temporary manifest and receipt evidence, fsyncs prerequisites, and atomically
renames the single complete manifest containing the receipt last. Therefore a
pre-commit stop cannot leave a manifest claiming success.

## Resume And Rollback

Resume requires an explicit conversion ID. It reopens only that journal,
validates root/source/archive/export/plan digests, verifies all completed
post-images, and repeats incomplete operations. If manifest commit already
occurred, resume verifies the exact committed receipt and advances to
completed without replaying target writes.

Rollback also requires the journal ID. It first validates every affected live
path. Created paths are removed only when their current digest equals the
journal post-image; replaced paths are restored only when their backup and
current post-image both authenticate. Any mismatch causes zero rollback
mutation and `recovery-required`. Rollback never touches V0 input or any
archive path. There is no reconstruction of V0 history from V1 content.

## Interface Contract

The closed bridge grammar is the frozen `release/contracts/v1/command-grammars.json`
bridge object. `inspect`, `preview`, and `version` are read-only. `export`
creates only new export/archive evidence. `apply` owns journal conversion,
`resume` owns remaining operations, and `rollback` owns matching post-images.
Usage errors exit 64; unsupported input exits 5; drift/conflict exits 4; invalid
state exits 3; unresolved V1 structure exits 2; internal and output failures
use 70 and 74.

## Observability And Kill Points

Machine output is deterministic and excludes absolute paths, time, random
values, raw command output, and V0 task fields. Test-only kill-point injection
stops after detection, export, archive, every filesystem operation, temporary
manifest/receipt write, and atomic commit. Tests snapshot all V0 inputs before
the operation and compare them after every failure, resume, and rollback.

## Alternatives Considered

1. Put conversion in `harness-core`. Rejected because SQLite and V0 semantics
   would become permanent dependencies.
2. Copy only `harness.db`. Rejected because committed WAL-only rows disappear.
3. Treat `.harness/` as owned. Rejected because a directory name is not
   provenance and could destroy foreign metadata.
4. Overwrite archive files on retry. Rejected because recovery evidence is
   write-once and retained indefinitely.
5. Best-effort rollback over target edits. Rejected because it would destroy
   human post-conversion work.


# US-109 Design: Freeze, Archive, Fresh V1

## Components and ownership

`harness-v0-migrate` owns only V0 recognition, exact capture, SQLite WAL
recovery in private staging, neutral export, and append-only archive custody.
It imports the core's public frozen repository-relative path validator so the
two binaries do not disagree on traversal, Windows device names, ADS, Unicode,
or `.git` rejection. It does not depend on core mutation code.

`harness-core` owns normal install/update recovery. Its only Phase 4 addition is
the first-install `--v0-archive-manifest` input and closed receipt fields. It
verifies manifest/payload/member digests as opaque bytes; it has no SQLite,
schema 1–13, changeset, or V0 row mapping code.

## Capture and export

Capture pins the repository root and opens every recognized source without
following links. Identity, size, and SHA-256 must match before/copy/after.
DB+WAL are copied to private staging; SHM is preserved as forensic evidence but
not used as SQLite recovery input. SQLite online backup turns the staged
DB+WAL into a standalone snapshot, including WAL-only commits. Export derives
from that snapshot and preserves exact SQLite value types and bytes.

`inspect`/`export` can use live frozen input. They can also use a published
archive manifest; encrypted inner verification/export additionally needs an age
identity. Caller output uses create-new semantics, so a pre-existing path is
never truncated.

## Archive publication

Custody is `.harness-v0-archive`, outside `.harness` core state. Initial custody
is created through a unique sibling stage containing a private key and a marker
HMAC-bound to repository root/device/inode, then atomically renamed no-replace.
An existing path without that authentication is foreign.

Each archive attempt:

1. creates a fresh unique `.staging-*` directory;
2. captures raw members and builds the standalone backup/export;
3. creates encrypted `archive.age` by default or explicitly acknowledged
   plaintext `archive.bin`;
4. writes the closed checksummed manifest and verifies staged bytes; and
5. atomically renames staging no-replace to a unique `v0-*` archive ID.

If power fails at step 1–4, no accepted final archive exists. Retry chooses a
new stage/ID and leaves abandoned or foreign bytes untouched. If step 5
succeeds, later attempts cannot replace that archive.

## Fresh install receipt

Core first install authenticates the archive custody marker and closed manifest,
checks the named opaque payload and required raw/backup/export members, then
copies only receipt metadata into the candidate V1 manifest. The ordinary Phase
3 operation plan, preview digest, journal, resume/rollback validation, and
manifest-last commit protect this receipt exactly like every other install byte.
Recovery therefore belongs to core install, not the bridge.

Authentication is shared as a contract, not an implementation dependency:
core applies the bridge-compatible root-identity/HMAC semantics through its
filesystem port while remaining free of SQLite, V0 readers, and bridge code.
Both archive and receipt contracts accept bridge release `1.0.0` exactly.
Unknown releases and capture enum values fail closed before preview or recovery.

The repository mode stays `fresh-v1` or `brownfield-v1`. This matters:
receipt presence says “this archive was preserved,” not “these V0 rows became
V1 operational state.”

## Rejected designs

- Automatic row-to-V1 mapping: rejected because operational semantics are not
  equivalent and archive evidence is sufficient.
- Bridge target writes and rollback journals: rejected because normal Phase 3
  install already owns safe V1 mutation/recovery.
- `.harness/legacy` custody: rejected because pre-existing content is ambiguous
  and core recovery owns `.harness`.
- Fixed archive names or overwrite-on-retry: rejected because a crash or
  attacker-prepositioned path could be adopted or destroyed.
- Windows capture emulation in Phase 4: deferred to Phase 7; this candidate
  compiles and exits 5 before repository capture.

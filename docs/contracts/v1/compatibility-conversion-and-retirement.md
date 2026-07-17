# Compatibility, Archive-Only Cutover, And Retirement Contract

Contract: `repository-harness-compatibility/v1`

## Fixed decisions and dates

Decision 0014 supersedes the automatic-conversion parts of Decision 0011 and
US-109. It preserves Decision 0012 retention and Decision 0013 capture/trust:

- compatibility window: `2027-01-01T00:00:00Z` through
  `2027-12-31T23:59:59Z`, inclusive;
- local V0 archives: write-once, checksum-verified, repository-owner custody,
  retained indefinitely, and never automatically deleted or relocated;
- complete bridge release asset set: retained and checked through
  `2028-06-30T23:59:59Z`, inclusive; and
- earliest Phase 8 eligibility: `2028-01-01T00:00:00Z`, after Phase 7 and every
  closure condition. Time alone never authorizes removal.

If general availability on every declared platform misses the window start, a
new decision must shift all coupled dates and preserve at least 365 supported
days. Implementation cannot calculate a replacement schedule.

## Freeze and exact capture

The operator stops V0 writes before capture. The bridge pins one repository-root
descriptor, walks recognized components relative to open parents without
following links, and retains descriptors through capture. For raw DB, WAL, SHM,
recognized changesets, and recognized provenance it compares identity, size,
and SHA-256 before/copy/after through the same descriptor. Ancestor replacement,
final replacement, or in-place mutation fails closed.

SQLite recovery occurs only in private staging with copied DB+WAL. SHM is
forensic-only; SQLite may create transient staging SHM. The online backup is a
standalone logical snapshot and the sole source for the neutral export. The
source database is never opened writable. Existing `.harness/legacy` and
`.harness/recovery` content is foreign and remains untouched.

## Append-only archive and read-only export

The reserved custody root is `.harness-v0-archive`. Its authenticated ownership
marker is bound to the repository root and a private custody key. If the path
already exists without valid ownership, `archive` fails and changes nothing.
Each attempt uses a new unique staging directory and atomically publishes to a
new unique final directory with no-replace semantics.

Cause and effect: a crash before publication leaves no accepted archive. Retry
uses fresh staging, so it neither adopts an abandoned directory nor overwrites
foreign or previously accepted bytes. A published archive contains exact raw
capture members, the WAL-aware standalone backup, and the neutral read-only
export with member and aggregate checksums.

`export` is the smallest access interface. It writes one new neutral export
from frozen live V0 input or a verified archive. The archived export reproduces
the exact neutral bytes, including WAL-only committed rows. V0 rows remain
historical evidence; no bridge code maps them into active V1 state.

## Fresh V1 and receipt binding

After publication, normal six-command `harness` install initializes V1 from
repository files. On first install only, `--v0-archive-manifest <path>` asks the
existing Phase 3 transaction to authenticate the closed manifest and opaque
payload digests and embed a write-once `v0_archive_receipt`. Core has no SQLite
or V0 parser, does not interpret V0 rows, and never creates `harness-v1.db`.
The receipt is committed with the ordinary fresh/brownfield manifest, last in
the recovery transaction.

## Confidentiality and tamper behavior

Default archive mode is `encrypted-age-x25519` for a repository-owner recipient.
The manifest records recipient fingerprints and ciphertext digest, never a
private identity. Plaintext requires both `--archive-plaintext` and
`--acknowledge-plaintext-recovery-risk`, and records
`plaintext-explicit-override` plus acknowledgement.

Archive tamper, digest mismatch, missing captured category, or confidentiality
record disagreement blocks archive `inspect`, archived `export`, and core
receipt binding. No bridge rollback exists because no bridge command mutates V1.

## Availability obligations

Release maintainers check all bridge binaries, checksums, authenticated index or
attestation, supported-input matrix, release notes, source tag, and reproducible
build instructions with exact UTC intervals of `0 < delta <= 7 * 86400`
seconds. At least once per calendar month, a 2-of-3 bridge-release-signed receipt
lists every complete-set category and all five supported platforms for
platform-scoped assets. Missing categories/platforms, decreasing times,
boundary gaps, or a failed check opens an obligation.

## Phase 8 gates

Phase 8 requires all of the following at one reviewed candidate:

1. Phase 7 accepted.
2. Authoritative time proves eligibility.
3. Support/recovery obligations are closed; archives remain readable.
4. No supported-range security, data-loss, or archive-integrity defect remains.
5. Weekly availability and the monthly signed receipt are current.
6. Separate human removal authorization and validation exist.
7. Re-inventory proves no required evidence will be lost.
8. Every local archive remains at the same path and bytes.

Failure of any item blocks V0 default-product removal. Even accepted Phase 8
cannot delete a local archive or end bridge-asset retention early.

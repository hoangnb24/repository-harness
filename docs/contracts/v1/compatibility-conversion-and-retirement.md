# Compatibility, Conversion Archive, And Retirement Contract

Contract: `repository-harness-compatibility/v1`

## Decision 0012 values

- Compatibility window: `2027-01-01T00:00:00Z` through
  `2027-12-31T23:59:59Z`, inclusive.
- Local conversion archives: write-once, checksum-verified, repository-owner
  custody, retained indefinitely, never automatically deleted or relocated.
- Complete bridge release asset set: retained and checked through
  `2028-06-30T23:59:59Z`, inclusive.
- Earliest Phase 8 eligibility: `2028-01-01T00:00:00Z`, after Phase 7 and every
  closure condition; time alone never authorizes removal.

If general availability on every declared platform misses the window start, a
new decision must shift all coupled dates and preserve at least 365 supported
days. Implementation cannot calculate a replacement schedule.

## Capture before conversion

The bridge first proves writer quiescence. It pins one repository-root file
descriptor, walks every recognized V0 component relative to its open parent
without following links, and retains the descriptors through capture. It reads
`(identity, size, SHA-256)` pre/copy/post through the same final descriptor and
then rechecks each namespace component through its pinned parent. The three
observations and component identities must be equal for raw DB, WAL, SHM,
every recognized changeset, and recognized provenance. Ancestor replacement,
final replacement, and in-place DB/WAL mutation fail. Unknown `.harness` state
is preserved but not claimed.

SQLite recovery starts only after raw capture passes. It works only inside the
private staging directory with staged DB+WAL. Staged SHM remains forensic-only;
SQLite creates any transient SHM it needs. The SQLite online-backup output is a
standalone logical snapshot and the sole source for neutral export. No capture,
recovery, or export opens the source database writable.

## Archive confidentiality

Default mode is `encrypted-age-x25519` for a repository-owner recipient. The
archive manifest and receipt record recipient fingerprints and ciphertext
digest, never the private identity. Plaintext requires both
`--archive-plaintext` and `--acknowledge-plaintext-recovery-risk`; the bridge
prints that repository/recovery data may be exposed and deletion loses
recovery, then records `plaintext-explicit-override` and acknowledgement.

Archive tamper, digest mismatch, missing captured category, or confidentiality
record disagreement blocks preview/apply/resume/rollback from using that
archive as recovery authority.

## Availability obligations

Release maintainers check all bridge binaries, checksums, authenticated index
or attestation, supported-input matrix, release notes, source tag, and
reproducible build instructions with exact UTC intervals of
`0 < delta <= 7 * 86400` seconds. Every check belongs to the receipt's declared
month, and the first/last checks cover the start/end boundary within the same
maximum interval. At least once per calendar month, a 2-of-3
bridge-release-signed receipt lists every complete-set category and all five
supported platforms for platform-scoped binaries/checksums, with every digest.
Missing categories/platforms, decreasing times, boundary gaps, or a failed
check opens an obligation; it cannot be represented as a successful receipt.

## Phase 8 gates

Phase 8 needs all of the following at the same reviewed candidate:

1. Phase 7 accepted.
2. Authoritative time proves eligibility, not a forecast or local test clock.
3. All support and recovery obligations are closed, including journals opened
   before the window ended.
4. No unresolved supported-range security, data-loss, or archive-integrity
   defect exists.
5. Weekly availability is current and the monthly signed receipt is valid.
6. Separate human removal authorization and validation exist.
7. Re-inventory proves no required history/recovery evidence will be lost.
8. Every local archive remains at the same path and bytes.

If any item fails, V0 default-product removal does not start. If all pass, Phase
8 may remove only the approved default V0 payload; it still cannot delete a
local archive or end bridge-asset retention early.

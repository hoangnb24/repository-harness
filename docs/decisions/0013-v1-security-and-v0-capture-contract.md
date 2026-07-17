# 0013 V1 Security And V0 Capture Contract

Date: 2026-07-17

## Status

Accepted

Decision 0014 preserves this decision's capture, WAL recovery, confidentiality,
custody, release-trust, and fail-closed requirements. It supersedes bridge
target mutation and conversion-journal mechanics; the normal Phase 3 core
install transaction now owns the archive receipt and all V1 writes.

## Context

Decision 0012 opened Gate G0, but dates and retention alone do not make a V1
release or a V0 conversion safe. Phase 1 needs one durable answer for four
questions before code is written:

1. Which keys authenticate permanent V1 payloads, and which keys authenticate
   the temporary bridge?
2. How does a client distinguish a current release from a replayed, frozen, or
   revoked release?
3. How is the first executable authenticated without trusting a key downloaded
   beside that executable?
4. What exact bytes constitute a recoverable V0 capture, especially when a
   committed SQLite transaction exists only in the WAL?

Without these answers, a later implementation could pass checksum tests while
still accepting one compromised signer, crossing bridge trust into core,
rolling a repository backward, executing an unauthenticated bootstrap, exposing
a plaintext archive, or backing up only the main database and silently losing
WAL-only data.

## Decision

### Disjoint trust domains

The permanent V1 core trust domain has three Ed25519 root keys and three
Ed25519 release keys. Each role has threshold 2-of-3. The bridge has a separate
three-root/three-release 2-of-3 bundle. A key ID is
`ed25519-sha256:<lowercase SHA-256 of the 32 raw public-key bytes>`.

Core and bridge keys, indexes, role names, monotonic counters, domain tags,
high-water marks, and reserved release-workflow identities are disjoint. A
cryptographically valid bridge signature on a core index is an authorization
failure, not a degraded success. Test private keys may exist only in clearly
marked deterministic test fixtures; no fixture key may appear in a production
bundle.

### Signed bytes and detached envelopes

Payload indexes are RFC 8785 canonical JSON. For a core index, the signed
message is:

```text
SHA-256(UTF-8("repository-harness-payload-index-v1") || 0x00 || JCS(index))
```

The bridge uses its distinct `repository-harness-bridge-payload-index-v1`
domain. Ed25519 signs the resulting 32 digest bytes. Signatures live in a
detached canonical JSON envelope that names the payload digest, trust domain,
role, sequence, algorithm, key IDs, and base64 signatures. The envelope never
contains or substitutes for the payload.

Verification uses a vetted Ed25519 implementation in strict mode. Before an
equation can count, both the public key and signature `R` must have canonical
encodings, must not be identity/small-order points, and must be in the
prime-order subgroup; `S` must be canonical, below the group order, and
nonzero. Identity, order-2, mixed-torsion, non-canonical, and zero-scalar
inputs fail closed. This prevents two malicious small-order keys with
`R = identity` and `S = 0` from forging a 2-of-3 envelope.

Concrete effect: changing JSON whitespace or object-member order preserves the
same JCS bytes and identity. Changing `docs/README.md` to a canonically
different Unicode spelling, adding a duplicate member, or changing a digest
changes or invalidates the signed document and is rejected.

### Freshness, rollback, rotation, and revocation

Every signed role has its own strictly monotonic sequence. A client persists a
high-water pair `(sequence, canonical digest)` for each trust-domain/role pair.
The same pair is idempotent; a lower sequence, or the same sequence with a
different digest, is rejected. An offline first install must pin either the
exact accepted index digest or a minimum role sequence in authenticated
bootstrap policy.

A rollback below a high-water mark is accepted only with a detached 2-of-3
root authorization naming the exact trust domain, role, rollback sequence,
canonical digest, and sequence of the currently active trusted root bundle.
The envelope must verify under that active bundle, and the signed
`root_bundle_sequence` must equal its sequence; a valid signature that names
any other root-bundle sequence is not authorization. The stored high-water mark
does not decrease. A root rotation must satisfy the old root threshold and the
proposed new root threshold over the same new bundle. A revocation becomes
effective only through a newer, root-threshold-signed bundle; signatures from
a revoked key do not count after that bundle is accepted.

For example, if `core-release` sequence 42 is pinned, a correctly release-signed
sequence 41 still fails. It succeeds only when a core-root 2-of-3 rollback
authorization names `core-release`, sequence 41, that index's exact digest, and
the active core root-bundle sequence. If the active root bundle is sequence 3,
an otherwise correct and validly signed authorization that names root-bundle
sequence 2 fails. A bridge-root authorization can never authorize this core
rollback.

### Bootstrap and release identity

Production V1 pipe-to-shell installation is prohibited. The bootstrap is an
immutable downloaded artifact. Before execution, the operator verifies a
pinned GitHub artifact attestation for the exact repository
`hoangnb24/repository-harness`, the reserved V1 protected-workflow identity once
promoted under its later gate, the artifact name, and the artifact digest. The
root key set and first-install pin are embedded in or supplied independently to
that authenticated bootstrap; a key downloaded beside the artifact is not a
trust anchor.

GitHub/Sigstore provenance authenticates the bootstrap/build context and may
supplement published payload evidence. It does not replace the V1 Ed25519
payload threshold. Existing V0 curl installers remain historical/current V0
behavior during the compatibility window; Phase 1 does not modify them.

The bootstrap verification order is exact: download the immutable file;
verify the pinned GitHub artifact attestation; verify exact repository,
protected-workflow, artifact, and digest identity; execute only that verified
file; then verify the separately rooted Ed25519-threshold payload index. The
core and bridge signature domains, root/release/rotation roles, tag namespaces,
and role-scoped sequence namespaces are closed. An added or reordered step, an
unknown field, or any core/bridge namespace crossover is a contract failure.

Phase 1 reserves, but does not create or claim protection for, the core
workflow `.github/workflows/harness-v1-release.yml` for Phase 2 and the bridge
workflow `.github/workflows/harness-v0-bridge-release.yml` for Phase 4. Their
machine lifecycle state is `reserved-absent`; either file appearing before its
later live-binding gate makes Phase 1 proof fail. Promotion to production
bootstrap acceptance requires all of: the reserved file, repository-protection
evidence bound to that workflow, a pinned GitHub artifact attestation bound to
the exact repository/workflow/artifact/digest, and the later phase's live
workflow-identity validation. The existing V0 release workflow remains a
separate current surface and is live-derived by the release inventory proof.

### Archive confidentiality and custody

Conversion archives are encrypted by default to a repository-owner age/X25519
recipient. The archive manifest and completed conversion receipt record
`encrypted-age-x25519`, recipient fingerprints, ciphertext digest, and custody
path. Plaintext requires an explicit bridge option plus a separate explicit
acknowledgement that plaintext can expose repository and recovery data and
that losing or deleting it can eliminate V0 recovery. The manifest and receipt
then record `plaintext-explicit-override` and the acknowledgement.

Archives remain write-once, checksum-verified, untracked recovery evidence at
their Decision 0012 path under repository-owner custody. No product command or
Phase 8 action automatically deletes, overwrites, truncates, or relocates one.

### Exact V0 capture

Before capture, every V0 writer is quiesced and the bridge proves that state.
The bridge pins one repository-root descriptor, opens every descendant
component relative to its already-open parent with no-follow semantics, and
keeps those descriptors open through verification. It never validates a path
and then reopens the final pathname independently. It copies the raw
`harness.db`, existing `harness.db-wal`,
existing `harness.db-shm`, every recognized changeset, and recognized installer
provenance. For every file it reads pre, copy, and post bytes from the same
anchored final handle and compares identity, size, and SHA-256. It then checks
each still-open component against its pinned parent descriptor. Any ancestor
swap, final replacement, source/WAL mutation, symlink/reparse point, size
change, or digest change fails closed before conversion mutation.

Only after those equalities pass may SQLite operate, and then only on the
private staged `harness.db` plus staged WAL. Staged SHM is forensic evidence and
is never recovery input. SQLite rebuilds transient shared-memory state and
produces a standalone online-backup snapshot from the recovered staged view.
That standalone snapshot is the logical recovery/export authority; the raw
files remain forensic and byte-recovery authority.

Concrete cause and effect:

1. A transaction commits to `harness.db-wal` but has not checkpointed.
2. Copying only `harness.db` omits that committed row.
3. Copying and identity-checking DB+WAL, then opening only that staged pair,
   makes the row visible.
4. SQLite online backup writes the row into the standalone snapshot.
5. Export reads the standalone snapshot, so conversion does not lose the
   WAL-only commit and never writes the source.

### Availability and retirement evidence

Release maintainers run a complete bridge-asset availability/integrity check at
least every seven exact 24-hour periods. Receipt timestamps are UTC-aware,
strictly increasing, inside the declared calendar month, separated by
`0 < delta <= 604800` seconds, and cover both month boundaries without a gap
over 604800 seconds. Once per calendar month, 2-of-3 bridge release keys sign a
receipt that binds every `complete_set` category, every supported platform for
binary/checksum categories, individual digests, check times, result, and
Decision 0012 retention deadline. An incomplete set or unsigned weekly log
does not satisfy the monthly receipt obligation.

Phase 8 remains blocked until every Decision 0012 gate passes, including Phase
7 acceptance, actual time eligibility, closure of supported recovery and defect
obligations, current bridge-asset availability evidence, separate removal
authorization/validation, and proof that local archives remain untouched.

## Alternatives Considered

1. One key for core and bridge. Rejected because bridge compromise would become
   permanent-core authorization.
2. One of three signatures. Rejected because one compromised release signer
   could publish an accepted payload or freeze a client.
3. Checksums or GitHub provenance as the payload root. Rejected because a
   checksum downloaded beside a payload is circular and provenance does not
   implement repository-owned threshold, rollback, or revocation policy.
4. Trust the highest sequence seen in the current process. Rejected because a
   clean restart would forget rollback history.
5. Back up the live main SQLite file only. Rejected because committed WAL-only
   state would be omitted and a changing source could yield a mixed-time copy.
6. Plaintext archives by default. Rejected because recovery evidence can
   contain repository operational history and target-owned content.

## Consequences

Positive:

- A single signer, bridge key, replayed index, or replaced source path cannot
  silently authorize core installation or conversion.
- First install has a non-circular trust path, while payload trust remains
  repository-owned and thresholded.
- WAL-only committed data is represented in the logical snapshot without
  treating SHM as durable truth or writing the source.
- Archive confidentiality, custody, availability, and Phase 8 proof are
  mechanically recordable.

Tradeoffs:

- Releases require threshold-signing ceremony, durable high-water state,
  rotation/revocation handling, and separate core/bridge operations.
- Conversion capture is slower because it hashes before, during, and after
  copying and requires writer quiescence.
- Repository owners must manage an age recipient and indefinite archive
  custody, or explicitly accept plaintext risk.

## Follow-Up

- Phase 1 freezes schemas, grammars, ledgers, test-only signatures, V0 schema
  bytes, parser matrices, and negative fixtures for this decision.
- Phase 2 may implement the permanent V1 verifier and six-command core only
  after Phase 1 proof passes; Phase 2 acceptance must replace the Phase 1
  entrypoint/workflow absence declarations with live source, CLI, and protected
  workflow evidence.
- Phase 4 may implement capture and conversion writes only in the isolated
  bridge; Phase 1 fixtures do not authorize conversion mutation, and Phase 4
  acceptance must replace bridge entrypoint/workflow absence with the matching
  live evidence.
- Production keys, signing, publishing, workflows, pilots, and Phase 8 removal
  require their later phase gates and are not created by this decision.

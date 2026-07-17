# Authenticated Payload And Destination Contract

Contract: `repository-harness-payload-index/v1`

## Authority and release identity

The authenticated index is the complete authority for a release. Directory
globs, source layout, an adjacent checksum, and a GitHub release page cannot add
an installable file. Core release identity is the tuple:

```text
(trust_domain, role, sequence, semantic_release, source_commit,
 payload_index_sha256)
```

Every asset binds a stable ID, exact source SHA-256, byte length, disposition,
role/template identity when relevant, and a destination rule. Destination
rules are either one exact path or an enumerated placeholder with a closed
value set. Wildcards, absolute destinations, `..`, platform-dependent case
selection, and runtime environment substitution are forbidden.

Example: an indexed template may declare destination candidates
`docs/decisions/` or an explicit brownfield mapping supplied in the preview.
It cannot declare `docs/**` and discover targets at runtime.

## Canonicalization and signatures

Security documents reject duplicate JSON member names, lone Unicode
surrogates, non-integer numbers, and integers outside the interoperable range
`[-9007199254740991, 9007199254740991]`. Within that closed value space, RFC
8785 canonical JSON is unambiguous. Object names sort by UTF-16 code units;
strings and integers use RFC 8785 serialization.

The core payload message is
`SHA-256("repository-harness-payload-index-v1" || NUL || JCS(index))`; bridge,
trust-bundle, rollback-authorization, and availability-receipt documents use
their separately declared domain strings. Ed25519 signs the 32 digest bytes.
Detached envelopes are themselves canonical JSON and bind exactly one payload
digest, trust domain, role, and sequence.

Two distinct authorized, non-revoked keys must verify. Duplicate signatures do
not count twice. A key ID must equal the SHA-256 of its raw public key. Core and
bridge bundles each contain three roots and three release keys with threshold
2. The two key-ID sets must be disjoint.

Signature verification is strict Ed25519 through a vetted library. Public keys
and signature `R` values must be canonical, non-identity, non-small-order, and
torsion-free; `S` must be canonical and nonzero. These checks occur before a
key can count toward threshold. For example, an envelope containing two
different key IDs whose public points are identity/order-2 and whose signatures
encode identity `R` plus zero `S` has zero valid signers, not two.

## Freshness lifecycle

High-water marks are persisted by trust domain and role. Equal sequence/equal
digest is idempotent; lower sequence or equal sequence/different digest fails.
Offline first install pins an exact index digest or minimum sequence. Rollback
needs 2-of-3 roots over the exact domain, role, release sequence, digest, and
the sequence of the active trusted root bundle, and never lowers the high-water
mark. Both the signature threshold and the signed `root_bundle_sequence` are
checked against that active bundle. Thus an authorization may verify
cryptographically yet fail semantically when it names an older or future root
bundle. Root rotation needs both old and new 2-of-3 thresholds. A revoked key
stops counting only after a higher-sequence root-threshold-signed bundle is
accepted.

The core tag namespace is `harness-v1-core-v*`; the bridge namespace is
`harness-v0-bridge-v*`. Their distinct protected workflow paths are frozen in
`bootstrap-identity.json`. Phase 2 makes the core workflow source
`source-present-unpromoted`; the bridge remains `reserved-absent` for Phase 4.
An artifact or attestation with the wrong repository, workflow, tag namespace,
trust domain, or role fails closed. The bootstrap file and its schema also
freeze the exact verification-order array, signature-domain strings, roles,
sequence namespaces, lifecycle states, reserved phases, and promotion-gate
requirements; additions and reordering are not extensibility points.

## Bootstrap

Production V1 instructions require download-to-file, pinned GitHub artifact
attestation verification for the exact repository/workflow/artifact digest,
then execution. `curl ... | sh`, `Invoke-WebRequest ... | Invoke-Expression`,
and equivalent stream execution are prohibited for V1. The authenticated
bootstrap supplies root anchors and first-install policy independently of the
payload host. GitHub/Sigstore provenance supplements but does not replace the
Ed25519 threshold.

This rule does not modify the current V0 installers in Phase 1.

Production core bootstrap acceptance remains blocked even though the Phase 2
workflow source exists. The repository-protection evidence and pinned
attestation for the exact repository/workflow/artifact/digest are external and
explicitly `required-not-present`. The workflow has read-only permissions,
proves before its promotion job, and its promotion job deliberately exits 1.
Current V0 release sources and the Phase 2 source workflow do not satisfy the
production promotion gate.

## Path-disposition ledger

`release/contracts/v1/path-dispositions.json` gives each current install or
release candidate exactly one value:

- `managed-v1`
- `optional-v1`
- `source-only`
- `target-owned-destination`
- `bridge-only-legacy`
- `forbidden-v0-operational`

Core artifact construction is an allowlist join between a verified core index
and ledger entries classified `managed-v1` or `optional-v1`. Missing ledger
rows, duplicate dispositions, unindexed files, destination disagreement, and
all other dispositions are errors. Bridge-only is not a core exception.

The V1 core accepts adjacent ledger bytes only when their canonical JCS digest
matches the digest supplied by the independent trust configuration. The
release-material transport cannot rewrite a row, reason, or disposition and
then choose the digest that makes its own rewrite authoritative.

Cause and effect: even if `scripts/schema/013-changeset-content-sha.sql` has a
correct digest and a valid bridge signature, its ledger disposition is
`forbidden-v0-operational` for core. The V1 core artifact build rejects it.

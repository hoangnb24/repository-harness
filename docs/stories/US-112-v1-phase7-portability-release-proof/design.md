# US-112 V1 Phase 7 Portability And Release Proof Design

Status: **Local execution proof implemented / remote five-platform proof and
promotion blocked**

## Domain Model

`PlatformLabel` is exactly `macos-arm64`, `macos-x64`, `linux-x64`,
`linux-arm64`, or `windows-x64`.

`CandidateIdentity` binds the exact source revision, V1 CLI identity, template
release, payload index, bridge identity, build inputs, and workflow revision.

`ArtifactProof` binds one platform label to the candidate identity, artifact
name, byte length, SHA-256, authentication record, build result, direct-binary
smoke, and installer result.

`FixtureCase` binds repository shape, path/line-ending conditions, operation,
expected manifest/audit result, mutation boundary, and normalized outcome.

`PromotionGate` is closed unless the artifact matrix, fixture matrix,
authentication checks, identity lock, release negatives, and the deferred
Phase 6 comparison obligation all pass for the same candidate.

## Application Flow

1. Freeze one candidate identity before platform proof begins.
2. Generate or select deterministic fixtures without target language-manifest
   interpretation.
3. Build each platform artifact from the same candidate source and declared
   inputs.
4. Authenticate checksums and payload/release identity before executing an
   installer or binary.
5. Run direct-binary and installer cases, normalize only documented
   platform-specific fields, and compare semantic outcomes.
6. Fail closed on missing artifacts, identity drift, unsupported mutation,
   path/line-ending loss, grammar divergence, or mutable release collisions.
7. Keep promotion closed until the deferred Phase 6 evidence is complete.

The direct executable enforces the first two runtime boundaries before parsing
even `--help`: `HARNESS_V1_ARTIFACT_SHA256` must match two reads of the current
executable, then `HARNESS_V1_PLATFORM` must match the compiled native OS and
architecture. For example, when both values are wrong, the digest error is
returned and the platform branch is never reached. Only after both pass can a
command inspect the repository.

Install, update, and scaffold accept release transport and independent trust
state only through absolute external paths. The directory adapter supplies
indexed bytes; the existing Ed25519 threshold verifier authenticates the
payload and test/production trust policy. The trust file cannot sit inside the
target repository. Unix commands then use the existing descriptor-anchored
mutation port. Non-Unix mutation still fails closed rather than emulating Unix
safety with path strings.

## Interface Contract

Phase 7 adds V1-only Bash and PowerShell checksum-first installers, fixture
runners, proof scripts, a closed non-production execution schema, and workflow
checks. It does not add a seventh V1 core command, merge the four bridge
commands into the core, change V0 installer behavior, or create target
telemetry. Existing install/update/audit/scaffold/status/version contracts
remain authoritative.

## Data Model

Tracked proof may contain closed manifests, platform labels, artifact names,
digests, public authentication material, normalized results, and redacted
reports. Production private keys, credentials, raw V0 databases/archives, and
decrypted recovery material remain external and untracked.

## UI / Platform Impact

macOS and Linux use the Bash V1 installer and direct binaries. Windows uses the
PowerShell V1 installer and `.exe` identities. Both installers authenticate the
checksum before platform selection and never claim provenance from a checksum.
Platform equivalence compares normalized manifest, audit, recovery, and
identity outcomes, not executable byte equality.

## Observability

Every proof command records candidate identity, platform, fixture, exact check,
exit result, and evidence path. No ordinary target repository is required to
emit telemetry.

## Alternatives Considered

1. Treat successful cross-compilation as platform proof. Rejected because it
   does not execute installer, path, recovery, or identity behavior.
2. Promote one platform first. Rejected because a missing declared artifact
   means the release candidate is incomplete.
3. Use Phase 7 fixtures as the deferred pilot experiment. Rejected because
   portability parity and real-agent efficacy are separate gates.

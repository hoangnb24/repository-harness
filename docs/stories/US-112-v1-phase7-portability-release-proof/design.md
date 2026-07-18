# US-112 V1 Phase 7 Portability And Release Proof Design

Status: **Engineering opened / proof implementation pending / promotion
blocked**

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

## Interface Contract

Phase 7 may add fixture runners, build/proof scripts, schemas, and workflow
checks. It does not add a seventh V1 core command, merge bridge grammar into the
core, or create target telemetry. Existing install/update/audit/status/version
contracts remain authoritative.

## Data Model

Tracked proof may contain closed manifests, platform labels, artifact names,
digests, public authentication material, normalized results, and redacted
reports. Production private keys, credentials, raw V0 databases/archives, and
decrypted recovery material remain external and untracked.

## UI / Platform Impact

macOS and Linux use Bash installers and direct binaries. Windows uses the
PowerShell installer and `.exe` identities. Platform equivalence applies to
contracted behavior, not byte equality between different executable formats.

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

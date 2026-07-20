# US-112 V1 Phase 7 Portability And Release Proof Design

> Decision 0018 supersedes Decision 0017 and exact-five equivalence as promotion
> requirements.
> A platform without native smoke proof is explicitly unsupported.

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
4. Generate GitHub/Sigstore build provenance only after artifact bytes are
   final, then verify the signed bundle and checksum before executing an
   installer or binary.
5. Run direct-binary and installer cases, normalize only documented
   platform-specific fields, and compare semantic outcomes.
6. Fail closed on missing artifacts, identity drift, unsupported mutation,
   path/line-ending loss, grammar divergence, or mutable release collisions.
7. Retain the bounded signed bundle and closed verification record so a
   collector can repeat verification without executing the artifact.
8. Keep promotion closed until the deferred Phase 6 evidence is complete.

The provenance sequence is deliberately causal. `capture_v1_build_receipt.py`
builds and copies the artifact and checksum but does not execute the artifact.
Capture and finalization disable Python bytecode before their first
repository-local import, and the workflow also exports
`PYTHONDONTWRITEBYTECODE=1`. Therefore importing receipt helpers cannot create
an untracked `scripts/__pycache__` between checkout and the clean-status gate.
The read-only build job uploads those final bytes, and an isolated attestation
job downloads and attests them with the exact-pinned v3.2.0 action commit. A
download-artifact v8.0.1 commit and upload-artifact v7.0.1 commit are also
exact-pinned in that privileged job; no moving action ref executes while OIDC
or attestation-write authority is present. Read-only jobs retain their scoped
moving-major artifact actions. The third read-only native job downloads the
same artifact and retained bundle. Its
finalizer calls `gh attestation verify` with one exact identity mode
(`--cert-identity`) plus the expected repository, source ref/digest, signer
digest, OIDC issuer, hosted-runner
policy, and retained bundle. It also checks the signed statement subject name,
SHA-256, manual-dispatch event, workflow path/ref, and transparency-log timestamp. A
failure stops before the finalizer invokes `--help`. The execution runner and
Windows installer guard repeat the same receipt/bundle verification before
their own execution paths.

Every workflow Python entry point uses the `python-path` output from
`actions/setup-python`; Windows never relies on a `python3` alias or a shebang.
Before the finalizer, installer, or native binary creates a subprocess, trusted
code constructs a new environment rather than filtering the runner
environment. It admits only `PATH`, temp variables, `LANG`/`LC_ALL`/`LC_CTYPE`,
and the Windows `SYSTEMROOT`/`WINDIR`/`PATHEXT`/`COMSPEC` essentials. Exactly
four trusted bindings may be added: artifact SHA-256, platform, release
directory, and trust-state path. It does not pass GitHub command-file channels,
Actions runtime/OIDC state, tokens, `PYTHONPATH`, `PYTHONHOME`, inherited home,
or cache variables. Thus even an unexpected diagnostic child cannot write a
later step's output/path/environment files or inherit ambient Python code or
attestation authority.

The trusted `gh` verifier is not candidate code: it receives an isolated
temporary home/config/state/cache root solely to prevent its device/config
bookkeeping from touching the checkout. That directory is removed when the
verification subprocess exits and is never forwarded to the artifact.

The direct executable enforces the first two runtime boundaries before parsing
even `--help`: `HARNESS_V1_ARTIFACT_SHA256` must match two reads of the current
executable, then `HARNESS_V1_PLATFORM` must match the compiled native OS and
architecture. For example, when both values are wrong, the digest error is
returned and the platform branch is never reached. Only after both pass can a
command inspect the repository.

The Bash V1 installer closes the destination namespace before publication. It
rejects a linked target root, `scripts`, or `scripts/bin`, then changes into
each physical directory so final publication is relative to the pinned `bin`
directory. Windows does not claim equivalent publication safety: after exact
checksum and native-platform validation, the PowerShell V1 installer returns a
deterministic controlled-unsupported refusal before inspecting or creating the
destination tree and contains no copy or move path. This avoids treating
reparse-point checks followed by path-based copy as race-free publication.

Install, update, and scaffold accept release transport and independent trust
state only through absolute external paths. The directory adapter supplies
indexed bytes; the existing Ed25519 threshold verifier authenticates the
payload and test/production trust policy. The trust file cannot sit inside the
target repository. Unix commands then use the existing descriptor-anchored
mutation port. Non-Unix mutation still fails closed rather than emulating Unix
safety with path strings.

Journal ownership validation is platform-neutral even though journal mutation
is not. Its deterministic `.harness/recovery/<operation-id>` formatter is a
private pure function available to every target; it performs no filesystem
operation. Unix-only descriptor access, directory creation, reads, writes,
renames, recovery replay, and mutation dispatch remain behind `#[cfg(unix)]`.
This lets Windows compile and validate data structure ownership without
creating a Windows mutation path or weakening controlled-unsupported refusal.

## Interface Contract

Phase 7 adds V1-only Bash and PowerShell checksum-first installers, fixture
runners, proof scripts, a closed non-production execution schema, and workflow
checks. It does not add a seventh V1 core command, merge the four bridge
commands into the core, change V0 installer behavior, or create target
telemetry. Existing install/update/audit/scaffold/status/version contracts
remain authoritative.

## Data Model

Tracked proof may contain closed manifests, platform labels, artifact names,
digests, the public Sigstore bundle, a bounded verification record, public
authentication material, normalized results, and redacted reports. The record
contains no GitHub token or credential. Production private keys, credentials,
raw V0 databases/archives, and decrypted recovery material remain external and
untracked.

## UI / Platform Impact

macOS and Linux use the Bash V1 installer and direct binaries. Windows uses the
PowerShell V1 surface only to authenticate the checksum, validate the native
`.exe` identity, and refuse publication before mutation. The runner may then
execute those same authenticated bytes directly for controlled-unsupported
results; it records no Windows installation claim. Neither path claims
provenance from a checksum. Provenance becomes `github-sigstore-attested` only
after the signed bundle passes exact identity and subject verification;
production signing remains blocked.
Platform equivalence compares normalized manifest, audit, recovery, and
identity outcomes, not executable byte equality. Each receipt contains the
closed normalized result payload as well as its recomputed digest. Exact-five
verification also consumes the independently verified build-receipt root and
cross-binds platform, target, runner, artifact name, artifact SHA-256,
attestation-bundle SHA-256, and provenance-verification-record SHA-256.
Windows controlled unsupported behavior is distinct and cannot satisfy
equivalence.

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

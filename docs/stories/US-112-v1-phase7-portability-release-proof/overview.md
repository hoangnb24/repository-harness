# US-112 V1 Phase 7 Portability And Release Proof

Status: **In progress: engineering opened / no Phase 7 acceptance or release
promotion**

## Current Behavior

Phases 1-5 are accepted. The Phase 6 framework is implemented, independently
reviewed, and accepted by the repository owner for sequencing under Decision
0016; its live P0-P7 efficacy evidence remains deferred and pending.

The repository now has a GitHub-native provenance gate in addition to the
fixture, build-receipt, and local execution slices. Three ordered exact-five
stages build without execution, attest the immutable downloaded bytes in an
isolated OIDC job, then verify and execute on the native runner. They verify the signed
bundle against the expected public repository, push event, workflow path/ref,
candidate/workflow SHA, platform artifact name, and SHA-256. Only successful
verification can finalize the build receipt or reach an installer/direct
binary call. The bundle and a closed byte-bound verification record remain in
the five-day receipt artifact; collectors repeat verification read-only.
All three third-party actions inside the privileged job are immutable: the
attestation action is pinned to its verified v3.2.0 commit, artifact download
to the verified v8.0.1 commit, and bundle upload to the verified v7.0.1 commit.
Moving-major artifact actions remain only in jobs with `contents: read`.

On a native host the execution slice then re-verifies the exact build receipt
and artifact checksum before any execution and verifies the platform label.
Unix hosts install through Bash before exercising all six core commands against
all ten Phase 7 fixtures. Windows authenticates the `.exe`, then the PowerShell
installer deterministically refuses before destination creation or publication;
the authenticated artifact is executed directly only to observe the contracted
controlled-unsupported command results. Signed test-fixture payloads and
independent test trust state are materialized outside each target repository.
Candidate subprocesses receive a constructed allowlist containing only process
launch, temp, locale, and Windows shell/system essentials plus four explicit
trusted `HARNESS_V1_*` bindings. GitHub command files, Actions runtime/OIDC
state, tokens, Python injection variables, inherited home, and cache state are
absent.
The GitHub/Sigstore result authenticates diagnostic build provenance only; it
does not make the artifact production-signed, promotable, or supported.

The five native platform rows are wired to produce closed receipts, but they have not
run for this candidate. Four Unix rows require the full normalized mutation
contract. The Windows row instead requires checksum-first PowerShell installer
refusal before destination mutation, followed by direct authenticated-binary
controlled-unsupported exit 74 before repository mutation. Its
distinct receipt keeps five-platform equivalence pending until a safe Windows
adapter and native evidence exist.

## Target Behavior

Build a deterministic Phase 7 proof stack that:

1. exercises the required repository-shape and path/line-ending fixtures;
2. builds exact core and bridge candidates for the five platform labels;
3. authenticates every artifact with verified GitHub/Sigstore build provenance
   and binds it to one payload/release identity;
4. proves Bash, PowerShell, and direct-binary behavior is equivalent at the
   manifest, audit, recovery, and unsupported-platform boundaries; and
5. refuses promotion unless deferred Phase 6 pilot evidence and every Phase 7
   release gate pass for the same candidate.

Example: a Windows binary compiling is not enough. The Windows fixture must
also preserve Unicode/spaces and CRLF/LF paths, authenticate the `.exe`, expose
the correct grammar and identity, and either perform safe supported operations
or fail before mutation with the contracted unsupported result.

Concrete failure example: if the Linux x64 bytes are replaced after
attestation, the artifact SHA-256 no longer matches the signed subject. `gh
attestation verify` fails, the receipt is not finalized, and neither `--help`
nor the installer runs. A matching checksum file cannot bypass that failure.

## Affected Users

- Release maintainers get exact pre-promotion evidence and immutable identity
  rules.
- Repository owners get equivalent installer and audit behavior across
  supported platforms.
- Pilot owners retain control of deferred live experiment custody and signing.
- Agents get deterministic fixtures rather than platform claims inferred from
  compilation alone.

## Affected Product Docs

- `docs/REFACTOR_PLAN.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0016-phase6-framework-acceptance-and-phase7-opening.md`
- `docs/stories/US-105-harness-v1-implementation/**`
- `docs/stories/US-111-v1-phase6-capability-evaluation/**`

## Non-Goals

- Running or inventing the deferred live P0-P7 results.
- Tagging, publishing, promoting, or using production signing keys.
- Claiming Phase 7 acceptance or supported-platform release status from this
  opening slice.
- Removing V0 or advancing Phase 8.
- Interpreting target language or package-manager manifests.

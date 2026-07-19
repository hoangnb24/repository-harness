# US-112 V1 Phase 7 Portability And Release Proof Exec Plan

Status: **In progress: local closed execution slice implemented; remote
five-platform evidence, acceptance, and promotion pending**

## Goal

Implement the deterministic portability and pre-promotion proof stack while
keeping tags, publishing, production signing, Phase 7 acceptance, and Phase 8
closed.

## Scope

In scope:

- Decision 0016 and the Phase 7 story packet.
- Exact fixture and platform matrices.
- Five-platform build/authentication/identity proof.
- Bash, PowerShell, and direct-binary parity.
- Promotion refusal when deferred Phase 6 or Phase 7 evidence is incomplete.

Out of scope:

- Live P0-P7 execution and owner signatures.
- Release tags, publishing, promotion, or production keys.
- V0 removal or compatibility-window changes.

## Risk Classification

Risk flags:

- Public contracts.
- Cross-platform behavior.
- Existing release and installer behavior.
- Weak proof until the complete platform matrix executes.
- Multi-domain release, bridge, core, installer, and workflow boundaries.

Hard gates:

- Validation requirements may not be weakened.
- No target mutation before artifact authentication and platform support
  checks.
- No promotion until deferred Phase 6 and complete Phase 7 proof both pass.

## Planning Mode

This high-risk story and its resume capsule own the cross-platform release
work. Ordinary repository tasks do not require this plan.

## Work Phases

1. Freeze the Phase 6 framework revision and Decision 0016 boundary.
2. Inventory existing fixtures, workflows, artifact names, and platform gaps.
3. Define closed Phase 7 evidence schemas and exact candidate identity.
4. Implement the fixture matrix and local platform-independent negatives.
5. Implement five-platform build, installer, and direct-binary proof.
6. Verify identity/equivalence and promotion refusal; obtain independent
   review before any separate release action.

The first bounded slice implements steps 3-4 only as a non-production fixture
contract. It adds exact candidate identity, ten byte-bound repository-shape
fixtures, five pending artifact/checksum placeholders, and fail-closed
promotion negatives. It does not execute or satisfy step 5, and it does not
assert any Phase 7 proof flag.

The build-receipt slice now implements build/checksum/help grammar plus
authenticated diagnostic provenance for step 5. A closed build receipt
separately binds (a) the exact candidate
source commit/tree, `Cargo.lock`, and command-implementation binding and (b)
the immutable revision and bytes of the protected-main workflow that actually
executed the capture. The receipt also binds the native platform tuple,
artifact, checksum, signed Sigstore bundle, closed verification record, and raw
help output. The capture
refuses a dirty tree, mutable/non-HEAD candidate, cross-target tuple, unsafe or
preexisting output. It does not execute even `--help`. After the artifact bytes
are final, a read-only build job uploads them, an isolated exact-pinned GitHub
action job generates provenance, and a separate read-only native job verifies
that signed bundle before it may run the non-mutating `--help` grammar
check. The collector reads either one receipt or exactly five downloaded
workflow directories, repeats signed-bundle verification, and never executes
the artifacts.

Both receipt entrypoints disable bytecode before repository-local imports, and
the workflow sets the matching environment defense globally. This keeps the
clean-status check causal: invoking capture cannot create its own untracked
Python cache and then reject the unchanged candidate.

The privileged job pins its artifact download to the verified v8.0.1 commit,
attestation generation to the verified v3.2.0 commit, and bundle upload to the
verified v7.0.1 commit. Its three `uses` references are therefore immutable;
moving-major artifact refs remain only in read-only jobs.

Cause and effect: a successful native `cargo build` produces bytes but no
receipt and no execution. A verified signed bundle changes provenance to the
schema-fixed `github-sigstore-attested`; only then can exact `--help` bytes set
`results.help_grammar_only` to `passed` and finalize the receipt. Installer and
full direct-binary proof remain `pending` in that build receipt, while platform
acceptance and every release/promotion/production-signing authority remain
blocked.

This completion slice closes the remaining locally executable path: the real
native binary refuses before command parsing unless its own SHA-256 and native
platform label match; external signed test release material drives real
install/update/scaffold commits through the existing recovery engine; Bash and
PowerShell V1 installer surfaces verify checksums before platform selection.
Bash publishes on Unix, while PowerShell refuses publication before destination
mutation because safe Windows handle-relative publication is not implemented.
One runner executes all six commands across the ten fixtures. It seeds inert
`package.json` and `Cargo.toml` files and proves they remain owner-owned rather
than interpreted. The normalized receipt binds the candidate commit/tree,
Cargo lock, command binding, exact workflow bytes, and each closed normalized
result payload.

Cause and effect: a local macOS pass proves that checksum-first Bash install,
native command execution, Unicode/space/LF/CRLF preservation, and normalized
manifest/audit/recovery/identity behavior work on that local host. It does not
prove Windows behavior, remote runner behavior, or platform acceptance. The
four Unix jobs must produce matching full normalized
contracts. Windows must record controlled unsupported behavior before
mutation, so five-platform equivalence remains pending until the safe adapter
exists. Even a five-receipt inventory cannot replace deferred Phase 6 live
evidence. Verified diagnostic provenance does not substitute for either gate.

The diagnostic workflow is discoverable on `refactor/harness-v1` without
default-branch installation. A push runs the costly jobs only when the
dedicated `.github/harness-v1-diagnostic-request` sentinel changes. It accepts
no candidate input: repository, event, ref, workflow ref, `github.sha`, and
`github.workflow_sha` must match exactly. The collector recomputes candidate
and workflow identities from checked-out Git objects, independently verifies
the downloaded build-receipt root, and requires each execution proof's
platform/target/runner/artifact-name/digest tuple to match its build receipt.
The isolated attestation job alone receives `contents: read`, `id-token: write`,
and `attestations: write`; build, verify/execute, and collector jobs are
contents-read only. Artifact upload/download names preserve exact
build-to-attest-to-verify-to-execute order. Every platform uses the explicit
`actions/setup-python` `python-path`, and candidate subprocess environments
are constructed from a minimal cross-platform allowlist. They receive only
launch/temp/locale/Windows essentials and exact trusted `HARNESS_V1_*` values;
GitHub command files, runtime/OIDC variables, tokens, Python injection, home,
and cache variables are absent. No stored key or repository secret is used.
The diagnostic contains no promotion job or
release path, so successful
diagnostics finish green while receipt and documentation authority fields keep
promotion blocked.

## Resume Capsule

- Objective: implement Phase 7 portability and release proof without promotion.
- Completed: Decision 0016 accepted; intake #9 recorded; fixture-only and build
  receipt slices; checksum/platform preflight; external release/trust adapters;
  Bash V1 installer and PowerShell controlled-unsupported installer surface;
  six-command/ten-fixture execution runner;
  normalized-payload receipt schema/verifier; refactor-branch sentinel
  diagnostic identity; exact-pinned privileged artifact transport and
  GitHub/Sigstore attestation generation;
  pre-execution verification; bounded bundle/verification evidence; Unix
  destination-link adversaries; exact build/execution tuple binding; Windows
  pre-publication refusal; PowerShell 5.1-safe separate refusal-stream capture;
  explicit plain-text minishell output;
  and local focused tests.
- Current evidence: local focused execution passes on macOS arm64. CI run
  `29688587069` at `fc22a466344f4b0297cb23b6b1da29f4ebc9c47b` verified
  provenance and completed six-command execution on all five platforms.
  Windows job `88197342173` then failed because redirected Windows PowerShell
  5.1 `-EncodedCommand` output used CLIXML, adding its marker and serialized
  startup progress around the exact refusal. The child now requests
  `-OutputFormat Text` while retaining separate .NET process streams and exact
  unfiltered stderr comparison. Windows mutation remains unsupported, final
  collection did not complete, and no platform is accepted.
  Separately, Pre-Merge run `29688588050`, job `88197179137`, passed the live
  Phase 5 six-group verifier and 19 trust adversaries, then failed because
  Phase 2's Phase 1 import and the Phase 7 release-proof import created
  repository-local `.pyc` files. The workflow-global
  `PYTHONDONTWRITEBYTECODE: "1"` guard and paired isolated-clone regression
  close that CI-hygiene defect. Both clones force the same in-checkout bytecode
  prefix: the unguarded clone must drift and the guarded clone must remain
  clean, proving the guard is causal without deleting primary-checkout files or
  changing authority.
- Remaining: a successful remote Windows refusal assertion and final receipt
  collection/equivalence, safe Windows repository mutation, deferred Phase 6
  live evidence, platform acceptance, review, and any
  separately authorized release action.
- Exact next action: `review this child commit; if another remote diagnostic is authorized, advance the sentinel in a normal child and push that exact candidate to refactor/harness-v1`
- Validation ladder: documentation and JSON checks; focused fixture/proof
  tests; installer/direct-binary tests; five-platform workflow; full premerge;
  stop at the first failed boundary.
- Decisions and assumptions: framework acceptance opens engineering only;
  deferred live experiments remain mandatory before acceptance/promotion.
- Blockers and owners: external pilot custody/signatures remain with repository
  owners; production release authority remains with release maintainers.
- Working state: this correction starts from published diagnostic head
  `47d3ae1a341e87cd1d76811aa7f21b4fba707fec`; no local compile result or
  execution receipt
  authorizes a tag, release, publish, production signing, promotion, platform
  acceptance, or live-pilot mutation.

## Stop Conditions

Pause for human confirmation if:

- a supported-platform claim would require unavailable execution evidence;
- a production key, tag, publish, or remote mutation becomes necessary;
- a fixture would weaken an earlier security/recovery contract;
- the deferred Phase 6 obligation would need removal rather than deferral.

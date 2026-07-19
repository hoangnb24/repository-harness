# US-112 V1 Phase 7 Portability And Release Proof Validation

Status: **Local native execution proof implemented / no remote five-platform
run or accepted platform / no acceptance or promotion**

## Proof Strategy

This bounded slice proves that a closed evidence document can bind one exact
candidate, every fixture byte, and exactly five unique pending platform
artifact/checksum records while refusing acceptance and promotion. For example,
changing the CRLF fixture to LF changes its digest and rejects the record;
duplicating `linux-x64` leaves `linux-arm64` missing and rejects the matrix.
It does not execute an artifact or prove a platform. Later implementation must
prove one exact candidate across every fixture and platform. A passing macOS
test cannot substitute for a missing Windows artifact, and a complete platform
matrix cannot substitute for the deferred Phase 6 pilot comparison.

The build-receipt continuation compiles one real native release artifact and
writes its exact SHA-256 sidecar without executing the artifact. After those
bytes are final, the exact-pinned v3.2.0 action commit generates GitHub/Sigstore
provenance in an isolated job that cannot execute candidate code. A separate
read-only native job uses the setup-python output explicitly; its finalizer
verifies the signed bundle before capturing raw
six-command JSON help. Its collector repeats that verification read-only for
one receipt or all five runner labels without executing downloaded binaries.
This is authenticated diagnostic provenance, not platform acceptance or
production signing; production signing remains blocked.

The local execution continuation now covers those behaviors on the current
native host. Each case installs a checksum-verified artifact, commits the
signed test-fixture payload, confirms idempotent update, commits one neutral
scaffold in an isolated surface, audits and reports ready state, reports exact
identity, and refuses a nonexistent recovery operation without mutation. The
runner snapshots every owner file, including spaces/Unicode and LF/CRLF bytes,
and seeds package manifests that must remain outside the V1 role map.

The finalized receipt says `github-sigstore-attested` only after `gh attestation
verify` authenticates the Sigstore bundle and its certificate/statement
identity. For example, changing only the recorded repository, workflow ref, or
artifact digest fails the closed verifier; supplying a checksum without the
bundle also fails. The exact-five collector must share candidate, workflow,
command, and normalized contract identity and match each execution proof to the
build receipt's platform, target, runner, artifact name, artifact SHA-256,
bundle SHA-256, and verification-record SHA-256. Until remote receipts exist,
platform proof remains zero.

Exact-five verification requires an independently resolved candidate SHA and
workflow revision, then recomputes the candidate tree, Cargo lock, command
binding, workflow path, and workflow byte digest from checked-out Git objects.
Five mutually consistent substituted receipts are therefore rejected. Each
fixture also includes its closed normalized command/recovery payload; fixture
and collection digests are recomputed from those payloads rather than trusting
arbitrary hash strings.

Four Unix receipts may share the full native contract. Windows must instead
record `controlled-unsupported-before-mutation`, exit 74 for repository
commands, zero mutation, and no manifest. Exact-five inventory verification
can therefore pass while `five_platform_equivalence` remains `pending`.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Closed schemas, duplicate-key rejection, exact candidate identity, native tuple/output safety, platform/path uniqueness, signed-subject/repo/workflow/ref/SHA/event/digest negatives, and authority-state negatives. |
| Integration | Fixture-only repository-shape inventory plus independently constructed closed verifier documents, checksum/help/bundle byte verification, exact build/execution/provenance tuple cross-binding, and no collector artifact execution. |
| E2E | Local Bash/direct-binary install-to-audit across all ten fixtures; Windows authenticates native bytes, proves PowerShell refusal before destination creation/copy/move, and runs only controlled-unsupported commands directly. |
| Platform | macOS arm64/x64, Linux x64/arm64, and Windows x64 exact artifacts. |
| Performance | Build/proof duration recorded; no performance acceptance claim in the opening slice. |
| Logs/Audit | Candidate/platform/check/evidence identities; no target telemetry. |

## Subject And Conditions

- Subject identity: exact future Phase 7 source, CLI, template, payload-index,
  bridge, build-input, and workflow candidate digest set.
- Condition identity: fixed fixture revision, platform runner image/toolchain,
  installer shell, permissions, and expected checks.
- Target owner: Repository Harness release maintainers; pilot evidence remains
  under the external owners from Decision 0015.

## Validation Ladder

| Order | Target-owned check | Applies when | Expected result | Failure route |
| --- | --- | --- | --- | --- |
| 1 | Documentation, schema, and diff checks | Every change | Exact status/gate language and closed records | Correct the owning document/schema. |
| 2 | Focused fixture and release negatives | Runner exists | Deterministic pass and fail-closed adversaries | Return to the owning script/contract. |
| 3 | Installer and direct-binary matrix | Artifact exists | Equivalent contracted outcomes | Reject the candidate platform artifact. |
| 4 | Five-platform and full premerge proof | Before acceptance | All platforms and earlier phases green | Keep Phase 7 unaccepted and rerun corrected identity. |

## Target-Owned Invariants

| Invariant | Owner | Check | Seeded or natural failure | Remediation | Exception path |
| --- | --- | --- | --- | --- | --- |
| Six-command core remains exact | V1 core | Grammar/source/release checks | Extra or missing command | Correct core/release packaging | None in Phase 7. |
| Bridge stays separate and four-command | V0 bridge | Bridge grammar/artifact scan | Core/bridge alias or merged payload | Correct packaging | None during support window. |
| No promotion with incomplete evidence | Release workflow | Pre-promotion gate test | Missing platform or deferred pilot result | Keep promotion blocked | Separate future decision cannot fabricate evidence. |
| Target content survives platform operations | Installer/core | Fixture before/after hashes | Path, line-ending, or ownership loss | Correct platform adapter | Platform remains unsupported. |

## Direct Feedback Routes

| Surface | Owner | Direct route | Success signal | Unavailable behavior |
| --- | --- | --- | --- | --- |
| Rust/core | Core maintainers | Cargo tests and platform builds | Tests/builds pass | Mark platform proof unavailable. |
| Bash installer | Installer maintainers | Installer fixture suite | Expected manifest/audit result | Keep Unix candidate unaccepted. |
| PowerShell installer | Installer maintainers | Windows runner refusal suite | Deterministic controlled-unsupported after authentication and before destination mutation | Keep Windows unsupported. |
| Release workflow | Release maintainers | Pre-promotion workflow tests | Immutable complete artifact set | No tag or publish. |

## Repeated Corrections

Repeated platform or packaging failures become target-owned fixture cases or
workflow negatives. Conversation history alone cannot waive or prove them.

## Gardening Contract

| Scope | Owner | Trigger or cadence | Runner | Bounded change policy | Validation | Convergence |
| --- | --- | --- | --- | --- | --- | --- |
| Platform/artifact matrix | Release maintainers | Candidate or workflow change | Repository release checks | Update only affected fixture/proof metadata | Focused then full matrix | Second identical run produces no artifact or metadata drift. |

## Fixtures

- Fresh and brownfield repositories.
- Nested instructions and docs-only repositories.
- Monorepo-shaped paths.
- Spaces, Unicode, LF, and CRLF cases.
- Custom-update and archive/bridge cases.
- Missing, mismatched, tampered, and colliding artifacts.

## Commands

```bash
python3 -m py_compile scripts/verify_v1_phase7_release_proof.py
scripts/verify-v1-phase7-release-proof.sh
tests/release/test-v1-phase7-release-proof.sh
scripts/verify-v1-phase7-release-proof.sh --require-promotable  # expected exit 2
tests/release/test-v1-phase7-execution-proof.sh
tests/release/test-v1-build-receipts.sh
tests/release/test-v1-build-receipt-workflow.sh
tests/release/test-v1-artifact-provenance.sh
tests/release/test-v1-attestation-workflow.sh
tests/release/test-release-workflow-contract.sh
tests/docs/test-doc-contracts.sh
scripts/verify-v1-phase6-evidence.sh --framework-only
```

## Acceptance Evidence

The schema, deterministic fixture inventory, verifier, and adversarial focused
test are implemented. The schema accepts only `fixture-only-non-production`
evidence and pins the readable V1 CLI, template-release, and bridge identities;
it cannot be switched into a platform-evidence mode. V1 artifact fixtures use
the `harness`/`harness.exe` identity, locked build input binds `Cargo.lock`, and
the V0 bridge remains a separate identity. All five artifact authentication/build/direct-binary/
installer results remain `pending`; fixtures say `not-run`; Phase 6 live P0-P7
evidence remains pending; every story proof flag remains unasserted; Phase 7
acceptance, tag, publish, production signing, and promotion remain blocked; and
Phase 8 remains closed.

The correction integrates the thirteenth closed schema into the Phase 1 schema
inventory and adds its one exact `source-only` path-ledger entry. This closes
the earlier full-premerge integration gap without making the Phase 7 fixture
evidence promotable or changing any platform result from `pending`.

The build-receipt continuation adds a separate fourteenth closed schema; it
does not loosen `phase7-release-proof-v1.schema.json` from
`fixture-only-non-production`. Eleven focused build-receipt adversaries, eight
provenance adversaries (including the installed `gh` parser), and twenty
static workflow adversaries cover dirty/mutable candidate boundaries,
separately bound candidate and executing-workflow revisions, approved-remote-branch
reachability, non-persisted checkout credentials, exact native tuples, safe
new external output, missing/duplicate platforms, candidate and input drift,
artifact/checksum/help substitution, unsupported claims, extra files,
duplicate keys, command fields, traversal, and symlinks. The workflow resolves
the candidate identity once. The corrected diagnostic uses a tightly scoped
push trigger on `refactor/harness-v1` and only when
`.github/harness-v1-diagnostic-request` changes. It has no arbitrary candidate
input and no `agent/*` or main authority. Exact repository, push event, branch
ref, workflow ref, candidate SHA, and workflow SHA must agree. Build,
verify/execute, and collector jobs check out that SHA with credential persistence disabled, verify
the immutable workflow object/path, upload bounded receipts for five days, and
download them under `contents: read`.

The added bytecode regression creates a temporary clean Git repository with no
`__pycache__` or `.pyc`, unsets both Python bytecode environment controls, and
forces repository-local cache placement. Capture reaches the deliberate
unsupported-platform rejection rather than failing its clean-status gate;
finalizer startup also creates no bytecode, and the fixture remains clean.

The provenance continuation extends the existing closed V1 build-receipt
schema and the closed Phase 7 execution-proof schema with a bounded
verification record. The build artifact bytes are finalized before
`actions/attest-build-provenance` runs at the verified v3.2.0 commit
`96278af6caaf10aea03fd8d33a09a777ca52d62f`. Its artifact download is pinned to
the verified v8.0.1 commit `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`
and its bundle upload to the verified v7.0.1 commit
`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`. Only the isolated attestation job
receives `contents: read`, `id-token: write`, and `attestations: write`; it
downloads immutable build output and never invokes repository Python or candidate
code. Build, verify/execute, and collection remain read-only. All platform Python
calls use the setup-python `python-path`. Candidate subprocesses use a fresh
minimal allowlist, so GitHub command-file paths, Actions runtime/OIDC state,
tokens, `PYTHONPATH`, `PYTHONHOME`, home, cache, and unrelated runner variables
never reach candidate code. The trusted `gh` process alone gets a temporary
home/config/state/cache root so its local bookkeeping cannot change the
checkout. No repository secret or private key is used. The retained public
Sigstore bundle and record contain no token. Finalization, the execution runner, the Windows installer
guard, and the collector all fail closed unless the exact signed subject and
repository/workflow/ref/SHA identity verify before execution.

No remote workflow run exists for this slice and no platform is accepted. A
local macOS arm64 test-fixture installer/direct-binary proof exists; native
Windows refusal evidence, exact-five build/execution/provenance cross-binding
and normalized equivalence, remote attestation evidence, deferred Phase 6
P0-P7 evidence, Phase 7 acceptance, and all tag/release/publish/production-
signing/promotion actions remain pending or blocked.

The local execution continuation adds a closed non-production schema under the
release test surface, V1-only Bash/PowerShell installers, direct self-digest
and platform preflight, external signed-test-payload adapters, and an
exact-ten-case runner/verifier. Focused local proof executes all six commands
for all ten cases and rejects checksum tampering, target-root/`scripts`/`bin`
links, mutually substituted exact-five identities, absent external identity or
build receipts, swapped platform/runner/target/artifact-name/digest tuples,
provenance and platform overclaims, normalized payload substitution, normalized
drift, and missing authentication. PowerShell's checksum/platform-before-refusal
order and absence of destination creation/copy/move are checked statically
locally; its native refusal test remains unrun until a Windows diagnostic.
No remote workflow was dispatched, so `platform_proof`, Phase 7 acceptance,
and all promotion authorities remain false.

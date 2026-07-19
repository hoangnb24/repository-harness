# US-112 V1 Phase 7 Portability And Release Proof Validation

Status: **Remote build attempt recorded / no complete five-platform run or
accepted platform / no acceptance or promotion**

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

CI attempt 2, run `29682593310`, executed against exact candidate
`47d3ae1a341e87cd1d76811aa7f21b4fba707fec`. Its macOS arm64/x64 and Linux
x64/arm64 build jobs succeeded. Windows failed in
`crates/harness-core/src/recovery.rs` before artifact upload because
platform-neutral journal ownership validation called the Unix-gated
`OsMutationPort::operation_root`. Consequently every attestation,
verification/execution, and collection job was skipped. The correction moves
only the pure deterministic operation-root formatter outside `#[cfg(unix)]`;
all filesystem mutation methods stay Unix-gated and non-Unix mutation stays
controlled-unsupported. A local Windows-target `cargo check -p harness-core
--all-targets` and a Phase 3 static cfg-boundary contract cover the regression.
The contract structurally
associates all outer attributes with the formatter's complete function item,
including restricted visibility and `const`/`async`/`unsafe`/`extern`
qualifiers. It also rejects `cfg` or `cfg_attr` on the required `apply` and
`recover` method items, normalizing the optional raw-identifier prefix so
`r#cfg` and `r#cfg_attr` cannot hide those items. Each method body must consist
of exactly one `cfg(unix)` dispatch and one `cfg(not(unix))` refusal, with no
other executable text or conditional region; the refusal then permits only
inert argument consumption followed by
`Err(MutationFailure::before_journal(...))`. Seeded restricted/public
visibility, qualifier, same-line/separate-line/nested block-comment, adjacent
line-comment, intervening-attribute, ordinary/raw conditional attribute,
comment-spaced raw attribute, alternative Windows cfg expressions,
conditionally absent method, unconditional/Windows-conditional filesystem
work before refusal, and marker-preserving non-Unix success variants all fail.
The scanner walks masked comments and ABI strings while retaining
original offsets for associated attribute bytes.

CI run `29685632567` at published candidate
`dd5648daa0db822f29a90fc47fcfbfce43db4a88` verified GitHub/Sigstore
provenance and completed the six-command execution proof on all five runners.
Windows job `88189458225` failed afterward only because the PowerShell 5.1 test
harness combined expected native stderr with the success stream while
`ErrorActionPreference=Stop`; the exact refusal became a terminating
`NativeCommandError` before exit, no-mutation, and input-hash assertions could
run. The correction uses `System.Diagnostics.Process` with separate asynchronous
stdout/stderr capture and asserts empty stdout, exact refusal plus platform
newline, exit 1, no destination state, and unchanged authenticated inputs.
The execution-proof contract pins the entire reviewed CRLF test at SHA-256
`059da9845613392a761a4016576d140c9be6c9957c430bcb6b192048696ad5a6`;
commented markers cannot substitute for active behavior. Seeded variants hide
the required test in `<# #>`, preserve old markers in trailing comments while
disabling redirect or loosening comparison, add native `*>&1`, or force exit 1.
Every byte-substituted variant fails the contract.

CI attempt 4, run `29688587069` at exact published candidate
`fc22a466344f4b0297cb23b6b1da29f4ebc9c47b`, again verified provenance and
completed the six-command proof on all five platforms. Windows job
`88197342173` reached the refusal capture, but its redirected Windows
PowerShell 5.1 `-EncodedCommand` minishell emitted CLIXML: stderr began
`#< CLIXML` and serialized `Preparing modules for first use` progress together
with the exact refusal. The correction adds only `-OutputFormat Text` to the
child arguments. It does not suppress progress or filter stderr, so unexpected
output still fails the exact comparison. Exit 1, empty stdout, exact refusal
plus platform newline, absent destination state, and unchanged authenticated
input hashes remain required. The exact reviewed CRLF test now hashes to
`23c2b91db380bef9528b72f7519f6f7c7ac021185a5bdddc97e46bf0685e4fb9`;
an `-OutputFormat XML` substitution is a seeded hash-regression adversary.

Remote attempt 5 at exact candidate
`fc177ab5c52780782419e6caafba1cec7ee8148c` completed all five native builds,
GitHub/Sigstore attestations, and exact provenance verifications, and the four
Unix platform paths passed. Windows failed only at the final refusal assertion:
stderr still began with `#< CLIXML`, contained the exact controlled-unsupported
refusal, and ended with serialized `Preparing modules for first use.` progress
records despite `-OutputFormat Text`. The output-format switch controls text
versus XML formatting of ordinary output; `$ProgressPreference` independently
controls progress updates and defaults to `Continue`. The encoded child command
therefore now starts with `$ProgressPreference = "SilentlyContinue"` before the
installer call. The parent does not suppress or parse stderr, so unexpected
errors remain visible and fail the exact comparison. Exit 1, empty stdout, the
exact refusal plus CRLF, absent destination state, and unchanged authenticated
input hashes are unchanged. The complete reviewed CRLF file now hashes to
`7651b11278475a26af45f0d9a14c7c909da1205b2881c87de624794127eb8b16`.
Seeded full-file-oracle adversaries remove the child setting, weaken it to
`Continue`, move it to the parent session, move it after installer execution,
or restore XML output; every variant is rejected.

The companion Pre-Merge run `29688588050`, job `88197179137`, completed all
six live Phase 5 proof groups and all 19 trust adversaries before the Phase 7
focused gate failed its final status-preservation assertion. Concretely, the
checkout already contained
`scripts/__pycache__/verify_v1_phase1_contracts.cpython-312.pyc` after the
Phase 2 import, and the Phase 7 test added
`verify_v1_phase7_release_proof.cpython-312.pyc`. The workflow now sets
`PYTHONDONTWRITEBYTECODE: "1"` in its top-level environment, so every Python
process in every Pre-Merge job inherits the guard. The workflow contract clones
two clean repositories into a temporary directory and forces
`PYTHONPYCACHEPREFIX` to the same relative in-checkout location in each. With
`PYTHONDONTWRITEBYTECODE` absent, the exact Phase 2-to-Phase 1 import followed
by the Phase 7 focused release-proof entry point must create `.pyc`, change Git
status, and trigger the focused test's status trap. A fresh clone runs the same
sequence with `PYTHONDONTWRITEBYTECODE=1` and must create no `__pycache__` or
`.pyc` and retain byte-for-byte-equivalent empty Git status. The negative
control prevents an inherited macOS `sys.pycache_prefix` from making the
positive case pass without proving causality. Static adversaries still reject
a missing, false, comment-only, or job-scoped setting. The regression removes
only its temporary clones; it does not delete or normalize anything in the
primary checkout.

No platform is accepted. A local macOS arm64 test-fixture installer/direct-
binary proof exists, and the remote run supplies five-platform provenance plus
six-command diagnostic execution. Native Windows installer-refusal completion,
final receipt collection/equivalence, deferred Phase 6 P0-P7 evidence, Phase 7
acceptance, and all tag/release/publish/production-signing/promotion actions
remain pending or blocked.

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
locally. Run `29685632567` exercised the native refusal but the parent test
harness terminated while capturing its expected stderr, so its post-exit
no-mutation/input-hash assertions and final collection remain incomplete.
`platform_proof`, Phase 7 acceptance, and all promotion authorities remain
false.

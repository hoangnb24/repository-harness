# US-112 V1 Phase 7 Portability And Release Proof Validation

Status: **Fixture contract and build-receipt infrastructure implemented / no
remote workflow run or accepted platform / no acceptance or promotion**

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

The build-receipt continuation can compile one real native release artifact,
write its exact SHA-256 sidecar, capture its raw six-command JSON help, and bind
those bytes to the exact committed inputs. Its verifier can collect the same
shape from all five runner labels without executing any downloaded binary.
This is infrastructure proof, not platform acceptance: building and asking for
help exercises neither installer behavior nor the six commands' full mutation,
recovery, audit, and unsupported boundaries.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Closed schemas, duplicate-key rejection, exact candidate identity, native tuple/output safety, platform/path uniqueness, digest and authority-state negatives. |
| Integration | Fixture-only repository-shape inventory plus synthetic single/exact-five receipt collection, checksum/help byte verification, and no artifact execution. |
| E2E | Bash, PowerShell, and direct-binary install-to-audit flows. |
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
| PowerShell installer | Installer maintainers | Windows runner fixture suite | Expected `.exe` and manifest result | Keep Windows unsupported. |
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
tests/release/test-v1-build-receipts.sh
tests/release/test-v1-build-receipt-workflow.sh
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
`fixture-only-non-production`. Nine focused Python adversaries and the static
workflow contract cover dirty/mutable candidate boundaries, separately bound
candidate and executing-workflow revisions, approved-remote-branch
reachability, non-persisted checkout credentials, exact native tuples, safe
new external output, missing/duplicate platforms, candidate and input drift,
artifact/checksum/help substitution, unsupported claims, extra files,
duplicate keys, command fields, traversal, and symlinks. The workflow resolves
the dispatch input once, proves the result is reachable from
`refs/remotes/origin/refactor/harness-v1`, and checks out that full SHA in
matrix and collector jobs with credential persistence disabled. Both jobs
fetch protected `main`, verify GitHub's immutable `workflow_sha` object and
workflow path, upload exactly five receipt directories for five days, and
download them for read-only collection under `contents: read`.

No remote workflow run exists for this slice and no platform is accepted.
Installer proof, full direct-binary proof, authenticated provenance, deferred
Phase 6 P0-P7 evidence, cross-platform equivalence, Phase 7 acceptance, and all
tag/release/publish/signing/attestation/promotion actions remain pending or
blocked.

# US-112 V1 Phase 7 Portability And Release Proof Validation

Status: **Executable fixture/candidate contract implemented / all live Phase 6
and Phase 7 results pending / no acceptance or promotion**

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

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Closed schema, duplicate-key rejection, exact candidate identity, platform/path uniqueness, digest and promotion-state negatives. |
| Integration | Fixture-only fresh/brownfield/nested/docs/monorepo/path/line-ending/custom-update/bridge inventory; no live operation claim. |
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
tests/docs/test-doc-contracts.sh
scripts/verify-v1-phase6-evidence.sh --framework-only
```

## Acceptance Evidence

The schema, deterministic fixture inventory, verifier, and adversarial focused
test are implemented. All five artifact authentication/build/direct-binary/
installer results remain `pending`; fixtures say `not-run`; Phase 6 live P0-P7
evidence remains pending; every story proof flag remains unasserted; Phase 7
acceptance, tag, publish, production signing, and promotion remain blocked; and
Phase 8 remains closed.

Full `scripts/validate-premerge.sh` was attempted after the focused ladder and
stopped at the accepted Phase 1 verifier's fixed twelve-schema inventory. Its
one-to-one Phase 1 path ledger would also need an explicit cross-phase decision
for the new contract file. This slice does not modify that excluded earlier-
phase verifier or ledger, so full premerge remains a named integration gap
rather than a passing claim.

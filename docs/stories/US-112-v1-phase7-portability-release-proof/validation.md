# US-112 V1 Phase 7 Portability And Release Proof Validation

Status: **Opening contract only / executable Phase 7 proof pending / no
promotion**

## Proof Strategy

The opening slice proves only that Phase 7 engineering is authorized under a
closed promotion boundary. Later implementation must prove one exact candidate
across every fixture and platform. A passing macOS test cannot substitute for a
missing Windows artifact, and a complete platform matrix cannot substitute for
the deferred Phase 6 pilot comparison.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Candidate identity, platform labels, normalized outcomes, closed evidence records. |
| Integration | Fresh/brownfield/update/audit/recovery fixtures and authenticated artifact selection. |
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

Commands will be added after the Phase 7 proof scripts exist. The opening slice
uses documentation contracts, Phase 1-6 regressions, and full premerge only.

## Acceptance Evidence

Decision 0016 and this packet open engineering only. No Phase 7 executable
evidence, five-platform acceptance, pilot comparison, tag, publish, or
promotion is claimed.

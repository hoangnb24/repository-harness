# US-112 V1 Phase 7 Portability And Release Proof

Status: **In progress: engineering opened / no Phase 7 acceptance or release
promotion**

## Current Behavior

Phases 1-5 are accepted. The Phase 6 framework is implemented, independently
reviewed, and accepted by the repository owner for sequencing under Decision
0016; its live P0-P7 efficacy evidence remains deferred and pending.

The repository now has a local deterministic execution slice in addition to
the earlier fixture and build-receipt slices. On a native host it verifies the
artifact checksum before any execution, verifies the exact platform label,
installs through the platform shell, and exercises all six core commands
against all ten Phase 7 fixtures. Signed test-fixture payloads and independent
test trust state are materialized outside each target repository. This proves
the local mechanism, not artifact provenance or supported-platform status.

The five native jobs are wired to produce the same closed receipt, but they
have not run for this candidate. Windows descriptor-anchored repository
mutation therefore remains controlled-unsupported until real Windows runner
evidence and the remaining safe adapter work pass.

## Target Behavior

Build a deterministic Phase 7 proof stack that:

1. exercises the required repository-shape and path/line-ending fixtures;
2. builds exact core and bridge candidates for the five platform labels;
3. authenticates every artifact and binds it to one payload/release identity;
4. proves Bash, PowerShell, and direct-binary behavior is equivalent at the
   manifest, audit, recovery, and unsupported-platform boundaries; and
5. refuses promotion unless deferred Phase 6 pilot evidence and every Phase 7
   release gate pass for the same candidate.

Example: a Windows binary compiling is not enough. The Windows fixture must
also preserve Unicode/spaces and CRLF/LF paths, authenticate the `.exe`, expose
the correct grammar and identity, and either perform safe supported operations
or fail before mutation with the contracted unsupported result.

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

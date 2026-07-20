# 0017 Proportional V1 Release Gate

Date: 2026-07-19

## Status

Superseded by Decision 0018.

## Context

Decisions 0015 and 0016 made eight P0-P7 cards across two externally signed
pilots and a five-platform proof matrix mandatory before V1 promotion. That is
more evaluation machinery than this template-first product needs for its first
release. It delays learning from a real release and makes maintaining the proof
system a larger project than maintaining V1.

## Decision

V1 promotion requires four proportional gates:

1. normal premerge validation passes for the exact candidate;
2. every platform claimed as supported builds and passes install, `audit`,
   `status`, and `version` smoke checks; a platform without that proof is
   explicitly unsupported rather than blocking other platforms;
3. one repository dogfood comparison uses a fixed starting revision, prompt,
   checks, baseline outcome, and candidate outcome, shows one concrete
   discoverability, context, validation, or human-attention benefit, and shows
   no functional regression; and
4. an independent reviewer approves the candidate and the actual release
   workflow generates and verifies provenance for released artifacts.

The P0-P7 framework, two-pilot enrollment, external evidence signing, and the
sentinel-triggered diagnostic workflow are no longer mandatory acceptance or
promotion gates. The historical Phase 5 baselines and Phase 6 framework remain
valid records; they are not rewritten as successful candidate evidence.

Decision 0015 still governs custody if a future evaluation uses sensitive V0
state. Decision 0016 still explains why Phase 7 engineering opened. This
decision supersedes their release-gate requirements.

## Concrete Cause And Effect

For example, if V1 claims Linux x64 and macOS arm64 support, both builds and
smoke checks must pass. A missing Windows adapter does not block release;
Windows is documented as unsupported. Separately, one dogfood task compares
the same task before and after V1. If the candidate finds the validation command
without human help and the task still passes its native tests, the behavior
gate passes. Eight scenario cards and a second repository are not required.

The old sentinel file also stops causing expensive diagnostic runs. A maintainer
may manually dispatch the diagnostic workflow while developing platform proof,
but that run is not release provenance and cannot promote a release.

## Consequences

- The gate tests actual product value with much less process.
- Supported-platform claims remain evidence-based.
- Unsupported platforms can ship later without pretending equivalence.
- The detailed evaluation framework remains available for future research or
  higher-risk releases.

## Follow-Up

- Record one dogfood comparison for the release candidate.
- Define the initial supported-platform set from passing native smoke checks.
- Attach provenance generation and verification to the actual release workflow.

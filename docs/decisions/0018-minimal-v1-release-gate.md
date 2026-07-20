# 0018 Minimal V1 Release Gate

Date: 2026-07-20

## Status

Accepted by the repository owner.

## Context

Decision 0017 reduced the original evaluation program but still required a
dogfood comparison, a separate independent-review concept, and provenance from
a distinct production release workflow. For this small, template-first project,
those requirements make the release process harder to understand and operate
than the product itself.

Windows also builds, but V1 intentionally refuses Windows repository mutation
until safe publication and recovery semantics exist. A passing refusal test is
not Windows install support.

## Decision

V1 promotion requires this minimal gate:

1. normal premerge validation passes for the exact candidate;
2. each platform claimed as supported passes its native build plus install,
   `audit`, `status`, and `version` smoke checks;
3. ordinary pull-request approval covers review of the candidate; no separate
   independent-review ceremony or evidence packet is required; and
4. GitHub Actions produces the downloadable binaries, SHA-256 checksums, and
   GitHub/Sigstore attestations. The repository owner may download and manually
   test those artifacts before an explicit publish action.

The dogfood comparison is removed from the V1 release gate. Phase 5 baselines,
the Phase 6 framework, and the broader five-platform diagnostic remain optional
engineering tools.

The initial supported set is macOS arm64, macOS x64, Linux x64, and Linux arm64.
Windows x64 remains experimental and explicitly unsupported for installation
until native mutation and recovery smoke checks pass.

This decision supersedes Decision 0017's release-gate requirements. Decisions
0012-0016 continue to govern compatibility, custody, and the history of the
refactor.

## Alternatives Considered

1. Keep the Decision 0017 dogfood and separate review/provenance requirements.
2. Block V1 until Windows implements Unix-equivalent safe mutation semantics.
3. Publish manually without workflow checksums or attestations.

## Consequences

Positive:

- Release proof is small enough to run and understand.
- Normal pull-request review replaces a special review process.
- The owner can test the exact downloadable artifacts before publishing.
- Windows work no longer blocks the supported Unix release.

Tradeoffs:

- V1 promotion will not include measured dogfood improvement evidence.
- Windows users receive an explicit unsupported result until its adapter is
  complete.
- Manual testing is owner judgment rather than a reproducible cross-platform
  proof; CI smoke checks remain the repeatable platform evidence.

## Follow-Up

- Run the four supported-platform native smoke checks on the release candidate.
- Make the CI-produced binaries, checksums, and attestations available for owner
  download and testing.
- Keep Windows controlled-unsupported until safe mutation and recovery pass.

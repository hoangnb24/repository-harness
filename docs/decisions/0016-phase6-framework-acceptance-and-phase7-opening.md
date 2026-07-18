# 0016 Phase 6 Framework Acceptance And Phase 7 Opening

Date: 2026-07-18

## Status

Accepted by the repository owner.

## Context

Decision 0015 required complete live P0-P7 candidate evidence before Phase 6
could close or Phase 7 could open. The repository-owned Phase 6 framework is
now implemented at `735e92a37fc44f243e5ce01e23af8b74a9e1de82`, independently
reviewed, and green under the trust-enabled full premerge suite. The repository
owner chooses to run the real two-repository experiments later and wants
portability engineering to proceed now.

Treating the unrun experiments as passing would manufacture efficacy evidence.
Keeping all Phase 7 engineering closed would also prevent independent fixture,
platform, and packaging work that does not depend on an efficacy result. The
phase boundary therefore needs two distinct gates.

## Decision

### Phase 6 framework acceptance

The repository owner accepts the implemented Phase 6 framework for sequencing
purposes. This acceptance covers the custody decision, portable target-owned
templates, evaluator/capture/verifier tooling, closed schemas, synthetic warm
capture, exact release-boundary checks, regression integration, and the clean
full-premerge result at the accepted framework revision.

Live P0-P7 candidate execution is deferred. The deferral is an open efficacy
obligation, not a passing result, an inapplicability finding, or permission to
rewrite the Phase 5 baselines. The Phase 6 evidence index remains
`candidate-results-pending`, and no candidate improvement or attention
reduction may be claimed from framework proof.

### Phase 7 engineering opens

Phase 7 engineering may start under US-112. It may create and validate:

- fresh, brownfield, nested-instruction, docs-only, monorepo-shaped,
  spaces/Unicode, line-ending, custom-update, and bridge fixtures;
- five-platform build and artifact-identity machinery;
- Bash, PowerShell, and direct-binary parity checks;
- checksum, payload-index, installer, audit, and unsupported-platform proof;
- pre-promotion workflow and negative-condition tests.

Opening engineering does not authorize a tag, publish, production promotion,
production signing key, mutable release, or claim of five-platform support.

### Acceptance and promotion remain closed

Phase 7 cannot be accepted and no release candidate can be promoted until both
sets of evidence pass for the same exact candidate:

1. the deferred Phase 6 live P0-P7 comparisons required by Decision 0015,
   including signed comparable conditions, negative-condition refusal, no
   functional regression, intervention totals, and the required concrete
   improvement; and
2. the Phase 7 fixture, artifact, installer, platform-equivalence,
   authentication, identity, and release checks.

Phase 7 evidence cannot retroactively stand in for Phase 6 efficacy evidence.
If deferred experiments fail, the candidate returns to its owning earlier
phase, the correction is made, and dependent Phase 7 proof is rerun against the
corrected exact identity.

### Relationship to Decision 0015

This decision supersedes only Decision 0015's rule that all Phase 7 engineering
must remain closed until live-card acceptance. Decision 0015 remains normative
for custody lanes, immutable warm masters, fresh derivatives, condition and
subject identities, live-state prohibitions, external trust/signing, and the
deferred live-card acceptance contract.

Phase 8 remains closed until Phase 7 acceptance and every Decision 0012 time,
support, recovery, security, archive-integrity, asset-retention, and separate
authorization/validation condition passes.

## Concrete Cause And Effect

1. A Linux-arm64 build fixture can be implemented before the real pilot run.
2. Its passing result proves only that the candidate artifact behaves correctly
   in that fixture.
3. It does not prove that a fresh agent resumes better in `e-inna-brain` or
   discovers a held-out capability in `harness-benchmark`.
4. The artifact may be merged as Phase 7 engineering, but it cannot be promoted
   until the deferred P0-P7 evidence and every Phase 7 gate pass together.

## Alternatives Considered

1. Mark the live experiments passed without running them. Rejected because it
   creates false evidence and breaks the fixed-card comparison contract.
2. Keep all Phase 7 work closed. Rejected because deterministic portability
   and packaging work can proceed without claiming efficacy or promotion.
3. Delete the Phase 6 live-card requirement. Rejected because the experiments
   are deferred, not removed; they remain mandatory before Phase 7 acceptance
   and release promotion.
4. Let Phase 7 fixtures substitute for pilots. Rejected because fixture parity
   and real agent outcomes answer different questions.

## Consequences

Positive:

- Portability work can begin immediately.
- Framework proof and live efficacy proof remain distinguishable.
- Release promotion still requires both real-pilot and five-platform evidence.

Tradeoffs:

- Phase 6 has a framework-accepted state with an explicit deferred efficacy
  obligation instead of one undifferentiated completion state.
- Phase 7 work may need rerun if later pilot experiments force a candidate
  correction.

## Follow-Up

- Execute US-112 without tagging, publishing, or claiming supported-platform
  release status.
- Run the deferred P0-P7 experiments before Phase 7 acceptance.
- Bind later pilot and platform evidence to the same exact candidate identity.

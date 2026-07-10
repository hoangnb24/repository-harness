# 0008 Self-Improving Harness Lifecycle

Date: 2026-07-10

## Status

Accepted

## Implementation Status

Implemented through `US-077`: replay-safe identity, selective proposal
decisions, story-to-backlog relationships, and explicit proof-backed atomic
completion are live. `US-078` through `US-080` remain planned, so recurrence
classification, outcome observation, daily health, and legacy reconciliation
are not yet current CLI behavior.

## Context

The existing improvement pipeline can generate deterministic suggestions from
friction, interventions, and audit findings, but it does not carry one issue
through acceptance, implementation, verification, closure, impact observation,
and later recurrence.

The live repository demonstrates the gap: audit is clean while `propose` still
emits patterns already stored as backlog items. Current proposal commits are
non-selective, proposal identity is not durable, backlog ids are local integers,
story verification is independent from backlog closure, and replay does not
preserve enough evidence identity to classify post-closure recurrence safely.

## Decision

Adopt a human-governed improvement lifecycle with these rules:

1. `propose` remains read-only unless one proposal key is explicitly accepted or
   rejected; bare bulk commit is invalid.
2. Explicit acceptance creates or reuses one backlog occurrence with status
   `accepted`, records an outcome-review schedule, and never persists every
   displayed proposal. Explicit rejection records one terminal occurrence and
   reason without creating implementation work.
3. A proposal key identifies the underlying issue. A separate stable backlog uid
   identifies one accepted, implemented, rejected, regression, or
   reconsideration occurrence.
4. Proposal matching is deterministic, conservative, Unicode-safe, and versioned.
5. Accepted occurrences retain structured links to the evidence they cover so
   old evidence can be explained and suppressed after closure.
   Default audit and proposal generation stay read-only; explicit audit-evidence
   recording creates lifecycle episodes so a cleared finding that later returns
   is genuinely new evidence.
6. Raw traces, friction, interventions, stories, and closed outcomes remain
   historical evidence and are not deleted to reduce proposal noise.
7. One story may resolve a backlog occurrence. Other stories may reference it
   without gaining closure authority.
8. Implemented closure of accepted resolved occurrences occurs only through an
   explicit story-completion operation. That operation requires the linked
   improvement intake and completed implementation trace, runs fresh
   verification, and on pass atomically records proof, marks the story
   implemented, and closes eligible accepted occurrences. Human rejection is a
   separate proposal-decision path.
9. Ordinary verification commands record proof but do not close lifecycle state.
10. Resolution evidence and measured outcome are separate records. Outcome
    observations are append-only; implementation proof never claims measured
    improvement.
11. New matching evidence after implementation is a regression. New evidence
    after rejection is a reconsideration. Both require a new human acceptance
    before becoming work.
12. Intakes, traces, occurrences, and evidence use stable cross-changeset
    identity. All lifecycle mutations participate in semantic changesets and
    fresh-database rebuild proof.
13. Cleanup is conservative and named. Ambiguous legacy rows are reported for
    human selection rather than rewritten automatically.

## Consequences

Positive:

- Handled issues stop competing with genuinely new improvement work.
- Every closure is explainable through accepted work and fresh proof.
- Regression history remains append-only and auditable.
- Fresh clones can reconstruct the same lifecycle decisions.
- Harness can measure whether implemented process changes actually helped.

Tradeoffs:

- Stable evidence identity and cross-changeset replay add schema and migration
  complexity.
- Explicit completion adds one lifecycle command instead of hiding closure as a
  side effect of verification.
- Legacy rows require conservative reconciliation before all old proposal noise
  can be classified automatically.

## Alternatives Considered

1. Continue committing every proposal. Rejected because it creates duplicate
   scope without a human decision.
2. Delete old traces or friction after implementation. Rejected because it
   destroys audit and learning evidence.
3. Close backlog work whenever any linked verification passes. Rejected because
   a planned story with an already-passing generic command could close unfinished
   work.
4. Reopen the old backlog row on recurrence. Rejected because it rewrites the
   historical fact that the earlier occurrence was resolved or rejected.
5. Use local numeric ids and closure timestamps only. Rejected because separate
   semantic changesets and fresh rebuilds cannot rely on those values as stable
   identity or evidence ordering.

## Supersession

When the corresponding E09 stories are implemented, this decision supersedes
the parts of decision 0007 that define bare
`propose --commit` as committing all proposals as `proposed` backlog items.
Decision 0007's remaining constraints still apply: proposal generation stays
deterministic, advisory, evidence-backed, and human-governed.

## Implementation

The dependency-ordered implementation plan is
`docs/stories/epics/E09-self-improving-harness-lifecycle/README.md`.

## Follow-Up

- Implement E09 in dependency order, starting with `US-073`.
- Update current-behavior docs only when each corresponding story lands.
- Mark decision 0007 partially superseded after selective acceptance and
  lifecycle closure are actually available in the released CLI.
- Keep H5 maturity partial until repeated measured outcomes demonstrate durable
  improvement.

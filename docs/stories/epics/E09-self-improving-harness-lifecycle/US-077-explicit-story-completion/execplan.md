# Exec Plan

## Goal

Make completion explicit, proof-backed, atomic, and replayable.

## Dependencies

- Blocked by: `US-075`, `US-076`.
- Consumes: accepted proposal occurrences, outcome schedules, designated resolver
  links, improvement intake, and completed implementation traces.
- Produces: verified closure events for `US-078` recurrence classification.
- Ready when: both prerequisite stories are implemented and dependency edges are
  complete.

## Scope

In scope:

- Typed `story complete` command and result.
- Completion-eligible status checks.
- Resolver intake/trace chain and all-target preflight checks.
- Fresh verification execution.
- Atomic story implementation and eligible backlog closure.
- Resolution evidence separate from actual outcome.
- Completion-time baseline for trace-count outcome schedules.
- Semantic changeset and rebuild parity.
- Minimal orchestrated run-state/contract alignment.

Out of scope:

- Proposal suppression and recurrence classification.
- Outcome measurement.
- Application UI completion controls.
- Automatic reopening or regression creation.

## Risk Classification

Risk flags:

- Existing behavior.
- Public contracts.
- Data model.
- Weak proof.

Hard gates:

- Automatic durable state transition.
- Validation and completion semantics.

## Work Phases

1. Add premature-pass, missing-intake/trace, ineligible-target, and rollback
   fixtures.
2. Implement story, intake, trace, resolver, and schedule preflight results.
3. Execute verification and write pass/fail safely.
4. Add atomic implemented-status, baseline, and backlog-closure transaction.
5. Add semantic operations and rebuild proof.
6. Align copied-story state, implementation trace, and completion order.
7. Update lifecycle docs and release proof.

## Stop Conditions

Pause for human confirmation if:

- Story completion cannot be atomic with backlog closure.
- An external orchestrator cannot establish `in_progress` without mutating root durable state.
- Verification requirements would need to be weakened.
- Completion would overwrite measured outcome or historical closure.

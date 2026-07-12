# Exec Plan

## Goal

Create explicit, replayable story-to-backlog relationships with unambiguous
closure authority.

## Dependencies

- Blocked by: `US-074`.
- Consumes: stable backlog occurrence identity.
- Produces: designated resolver and reference relationships for `US-077`.
- Ready when: `US-074` is implemented and its dependency edge is complete.

## Scope

In scope:

- Additive `010-story-backlog-links.sql` migration and constraints.
- Link/unlink/query CLI behavior.
- Stable uid changeset operations.
- One designated resolver per backlog occurrence.
- Detailed relationship query output.

Out of scope:

- Story completion and backlog closure.
- Multi-resolver or all-of aggregation.
- Application UI relationship editing.
- Automatic inference from story or backlog prose.

## Risk Classification

Risk flags:

- Data model.
- Existing behavior.
- Public contracts.
- Weak proof.

Hard gates:

- Durable relationship migration.
- Closure-authority semantics.

## Work Phases

1. Add failing schema and command-contract tests.
2. Add typed relationship values and repository methods.
3. Add migration 010, constraints, and indexes.
4. Add link/unlink/query CLI behavior.
5. Add semantic operations and rebuild support.
6. Update docs and installer proof.

## Stop Conditions

Pause for human confirmation if:

- More than one resolver is required for a real backlog occurrence.
- Existing records need ambiguous automatic links.
- Removing a link would require rewriting historical closure evidence.
- The relationship cannot be rebuilt without local numeric-id assumptions.

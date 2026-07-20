# 0003 Generic Spec Intake Harness

Date: 2026-05-05

## Status

Accepted for its stack-neutral consumer boundary. Its mandatory intake, story,
and proof loop is superseded by
`0019-repository-centered-default-workflow.md`.

## Context

Harness v0 originally shipped with a project-specific `SPEC.md`, product docs,
candidate epics, architecture assumptions, and validation examples. That made
the harness useful for the first project but too specific to reuse as the outer
shell for a new project.

The desired direction is a default harness that can wait for any user-provided
spec, derive product docs from that spec, and then continue with the same
intake, story, proof, and decision loop.

## Decision

Remove the tracked project-specific spec and pre-sliced product domains from
Harness v0.

The harness now starts with:

- No baked-in `SPEC.md`.
- Empty product docs except for intake guidance.
- Generic story and epic examples.
- Stack-neutral architecture discovery rules.
- Stack-neutral validation columns.
- A source hierarchy that treats a future user-provided spec as input material,
  not permanent living truth.

## Alternatives Considered

1. Keep the original `SPEC.md` as an example. Rejected because examples can be
   mistaken for current product truth.
2. Move the original product docs into an examples folder. Rejected for now
   because the user asked for a clean default harness.

## Consequences

Positive:

- The repository is easier to reuse for any new project.
- Future specs can define their own product domains and stack.
- Agents are less likely to confuse template truth with product truth.

Tradeoffs:

- The harness has fewer concrete examples until the next spec is supplied.
- The first spec intake must create product docs and candidate epics before
  implementation planning can be precise.

## Follow-Up

- Add a spec-intake template if repeated projects reveal a stable format.

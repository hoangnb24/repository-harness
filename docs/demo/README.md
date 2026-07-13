# Harness Demo Walkthrough

This walkthrough shows the kind of transformation Harness v0 is designed to
support. It is an example only. It is not an accepted product contract for this
repository.

## Input

A human brings a small product idea:

```text
Build a simple team task tracker where people can create tasks, assign them to
teammates, change status, and see what is overdue.
```

Without a harness, an agent might jump directly into framework selection,
database schema, UI scaffolding, and tests all at once.

Harness v0 asks the agent to slow the work down just enough to make it
inspectable.

## Intake

The input is classified as a new spec because it introduces a new product idea
with no existing product contract.

The first output should not be app code. It should be a spec-intake note using
`docs/templates/spec-intake.md`.

Example intake shape:

```text
Type: new spec
Lane: normal
Reason: creates a new product surface but does not yet touch auth, payments,
data migration, or external provider behavior.
Candidate product docs:
- docs/product/overview.md
- docs/product/tasks.md
- docs/product/assignment.md
Candidate epics:
- E01 Task capture and status tracking
- E02 Assignment and ownership
- E03 Overdue visibility
Validation shape:
- Unit proof for task status rules
- Integration proof for task persistence
- E2E proof for create, assign, and complete task flow
```

## Product Contract

After intake, the agent derives small product docs instead of treating the
original prompt as permanent truth.

Example product contract fragments:

```text
docs/product/tasks.md

A task has a title, status, assignee, due date, and timestamps.
Supported statuses are todo, in_progress, done, and canceled.
Only open tasks can become overdue.
```

```text
docs/product/assignment.md

A task may be assigned to one teammate.
Unassigned tasks remain visible in the team backlog.
Changing assignee does not change task status.
```

## Story Packet

Once the product contract is clear enough, the agent creates a story packet from
`docs/templates/story.md`.

Example story:

```text
Story: US-001 Create a task
Lane: normal
Product contract: A teammate can create a task with title, optional assignee,
optional due date, and default status todo.
Acceptance criteria:
- Creating a task with a title succeeds.
- Creating a task without a title fails with a clear validation error.
- A new task starts in todo status.
- A created task appears in the team backlog.
Validation:
- Unit: task creation rules
- Integration: persistence and validation boundary
- E2E: create task from the visible task surface
```

## Proof Matrix

The story then appears in the durable proof matrix so behavior and proof stay
linked:

```bash
scripts/bin/harness-cli story add --id US-001 --title "Create a task" --lane normal --contract docs/product/tasks.md
scripts/bin/harness-cli query matrix
```

Example row:

```text
| US-001 Create a task | docs/product/tasks.md | yes | yes | yes | no | planned | none |
```

The row should not be marked implemented until proof exists.

## Decision Record

If the team chooses a stack, data model direction, or important product rule,
the agent records that decision under `docs/decisions/`.

Example decision:

```text
Decision: Tasks use a small explicit status set instead of free-form labels.

Reason: status drives overdue behavior, filtering, and validation, so the first
version needs a predictable state model.
```

## Implementation

Only after the contract, story, and proof shape are clear should implementation
begin.

For Harness v0, that distinction matters. This repository deliberately does not
ship with application folders, package scripts, CI, or test commands. Those
should arrive only when a real story selects a real stack and needs them.

## Harness Delta

A change request also asks whether the harness itself should improve.

If this demo revealed that many projects need the same intake example, the
right follow-up might be:

```text
Add a reusable example-spec walkthrough or starter fixture.
```

Small improvements can be made directly. Larger process changes should be
recorded with `scripts/bin/harness-cli backlog add`.

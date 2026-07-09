# Guided Intake Draft UI Design

## Direction

Build the first slice of Guided Intake as draft-only UI inside the existing
Command Center. It should help the user shape intent without becoming a second
source of truth.

## Scope

- Add a `Guided Intake` view tab beside `Work Board`.
- Capture rough idea, audience, outcome, non-goals, and validation proof.
- Show a live story draft preview and a normal-lane explanation.
- Do not create durable intake/story records.
- Do not add backend endpoints, database schema, or automatic Symphony starts.

## Architecture

The UI is a focused React component under `features/symphony`. It owns local
draft state only. `main.tsx` owns the board/intake view switch and clears the
selected task when entering intake.

## Validation

Use TDD with Playwright:

- RED: guided intake tab missing before implementation.
- GREEN: fill intake answers and assert the draft preview updates.
- Full proof: build, e2e, desktop smoke, detector, Rust workspace checks.

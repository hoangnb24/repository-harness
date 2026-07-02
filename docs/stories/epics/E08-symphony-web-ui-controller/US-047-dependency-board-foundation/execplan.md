# Exec Plan

## Goal

Create the dependency-aware board state foundation for the Symphony Web UI
Controller.

## Scope

In scope:

- Harness schema for direct story dependency edges.
- Symphony board derivation over Harness stories, dependency edges, and run
  state.
- Cycle detection with simple blocked reasons.
- CLI inspection with `harness-symphony work board`.
- Unit tests for ready/blocked/cycle/run-state derivation.

Out of scope:

- Browser UI.
- HTTP API server.
- Run start from the UI.
- Codex event streaming.
- PR provider polling.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Data model.

## Work Phases

1. Add story docs and durable story record.
2. Add Harness dependency schema migration.
3. Implement board derivation in Symphony.
4. Add CLI command and tests.
5. Run focused Rust validation.
6. Update story proof and trace.

## Stop Conditions

Pause for human confirmation if:

- Dependencies require deleting or rewriting existing story records.
- The schema needs more than direct blocker edges for the MVP.
- Validation requirements need to be weakened.

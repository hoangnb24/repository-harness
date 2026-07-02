# US-050 Run Start And Codex Event API

## Status

implemented

## Lane

high-risk

## Product Contract

The Web UI must let a user start a Ready task, enforce the one-active-task MVP
rule, and surface Codex App Server events from the existing Symphony event log.
The backend must reuse Symphony run preparation, state locking, and run
execution instead of becoming a second runner.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Acceptance Criteria

- `POST /api/tasks/<story-id>/start` prepares a real Symphony run and returns
  the run id.
- Starting a task is refused when another run is active.
- The board model can show the prepared/running task as `In Progress`.
- `GET /api/runs/<run-id>/events` returns parsed Codex App Server JSON-RPC
  events from `APP_SERVER_EVENTS.jsonl`.
- The browser UI start button calls the start endpoint for Ready tasks.
- The browser UI polls and displays recent events for the selected active run.

## Design Notes

- Commands: `harness-symphony web`; `POST /api/tasks/<story-id>/start`.
- Queries: `GET /api/runs/<run-id>/events`.
- API: start returns `202 Accepted`; active-run conflicts return `409`; missing
  event logs return an empty events list.
- Tables: reuses `run_state`.
- Domain rules: one active run is enforced before git/worktree preparation.
- UI surfaces: task detail start button and recent event list.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Web route tests for start path, event parsing, active-run conflict, and static/API routing. |
| Integration | Start endpoint prepares a real run in a temporary git repo and records an active run. |
| E2E | Deferred to `US-053`. |
| Platform | Live loopback smoke verifies built UI, board API, and empty event endpoint. |
| Release | Not required. |

## Harness Delta

No process change.

## Evidence

- `cargo test -p harness-symphony web -- --nocapture` passed: 9 web tests,
  including a temporary git repo start request that returned `202 Accepted` and
  recorded an active run.
- `npm --prefix crates/harness-symphony/web-ui run build` passed.
- `cargo test -p harness-symphony` passed.
- `cargo test --workspace` passed.
- `cargo fmt --check` passed.
- `cargo clippy --workspace -- -D warnings` passed.
- Live loopback smoke on `127.0.0.1:43218` verified `/`, `/api/board`, and
  `/api/runs/run_missing/events`.

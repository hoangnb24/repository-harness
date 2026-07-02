# US-049 Browser Board And Task Detail UI

## Status

implemented

## Lane

high-risk

## Product Contract

The local Web UI must give users a browser board for Symphony tasks without
creating tasks or duplicating Harness state. The first browser slice shows the
board states, selectable task cards, dependency context, proof/run metadata, and
disabled start affordances for non-ready tasks.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Acceptance Criteria

- A Vite React frontend exists for the Web UI Controller.
- The UI uses shadcn-style local components and lucide icons.
- The board consumes `GET /api/board`.
- Tasks are grouped into Ready, Blocked, In Progress, Review, Needs Attention,
  and Done columns.
- Selecting a task shows a detail panel with blockers, unblocked tasks, lane,
  proof state, run id, and reason.
- The local `harness-symphony web` server serves the built UI at `/`.
- The UI does not create tasks.

## Design Notes

- Commands: `npm --prefix crates/harness-symphony/web-ui run build`;
  `harness-symphony web`.
- Queries: `GET /api/board`.
- API: no new API shape beyond `US-048`.
- Tables: no new tables.
- Domain rules: task creation remains out of scope; start control is displayed
  but disabled unless the selected task is Ready.
- UI surfaces: browser board and task detail panel.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript build compiles React components. |
| Integration | Rust web tests cover static UI serving and API routes. |
| E2E | Deferred to `US-053` because the browser bridge was unavailable in this session. |
| Platform | Live loopback smoke serves `/`, built JS, and `/api/board`. |
| Release | Not required. |

## Harness Delta

No process change. The browser verification gap should be closed by `US-053`.

## Evidence

- `npm --prefix crates/harness-symphony/web-ui install` completed with 0
  vulnerabilities reported.
- `npm --prefix crates/harness-symphony/web-ui run build` passed.
- `cargo test -p harness-symphony` passed: 55 tests.
- `cargo test --workspace` passed: 90 tests.
- `cargo fmt --check` passed.
- `cargo clippy --workspace -- -D warnings` passed.
- Live loopback smoke on `127.0.0.1:43218` verified `/` serves the built Vite
  app and `/api/board` includes `US-049`.
- In-app browser visual verification could not run because the browser bridge
  was unavailable in this session; full browser E2E remains assigned to
  `US-053`.

# US-057 Dependency Graph Sidebar View

## Status

implemented

## Lane

normal

## Product Contract

The Symphony Web UI Controller sidebar must expose dependency graph context from
the existing board API so users can see direct blocker and downstream task
edges without leaving the Kanban-first controller.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`
- `docs/design/symphony-web-ui-controller/README.md`

## Acceptance Criteria

- The workspace sidebar includes a dependency graph section.
- Dependency graph rows are derived from `GET /api/board` item `blockers` and
  `unblocks` fields.
- The graph shows direct blocker-to-task and task-to-downstream relationships.
- Selecting a graph row opens the same selected-task detail rail used by board
  cards.
- Empty dependency graphs render a clear empty state without breaking the board.

## Design Notes

- Commands: `harness-symphony web`, Vite build, and Playwright E2E.
- Queries: `GET /api/board`.
- API: no new runtime API.
- Tables: no new tables.
- Domain rules: dependency truth remains backend-owned; the browser only renders
  graph edges already present in board data.
- UI surfaces: local React controller sidebar in
  `crates/harness-symphony/web-ui`.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-057 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript build. |
| Integration | Vite production build. |
| E2E | Playwright sidebar dependency graph flow with mocked board edges. |
| Platform | Browser-rendered local UI through Playwright. |
| Release | Not required. |

## Harness Delta

No harness process change expected.

## Evidence

- `npm --prefix crates/harness-symphony/web-ui run build` passed.
- `npm --prefix crates/harness-symphony/web-ui run e2e` passed with 2
  Chromium tests, including a mocked sidebar dependency graph edge-selection
  flow.
- `scripts/bin/harness-cli story verify US-057` passed.
- `git diff --check` passed.

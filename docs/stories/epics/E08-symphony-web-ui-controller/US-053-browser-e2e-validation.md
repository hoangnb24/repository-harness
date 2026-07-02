# US-053 Browser E2E Validation

## Status

implemented

## Lane

high-risk

## Product Contract

The Web UI Controller needs browser-level proof that the local Vite React UI is
served by `harness-symphony web`, loads board data, renders board states, and
supports task detail inspection.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Acceptance Criteria

- Playwright is configured for the Web UI package.
- The Playwright web server starts `harness-symphony web`.
- A Chromium E2E test opens `/`.
- The test verifies board columns for Ready, Blocked, In Progress, Review,
  Needs Attention, and Done.
- The test filters for a task, selects it, and verifies the detail panel and
  Start control.

## Design Notes

- Commands: `npm --prefix crates/harness-symphony/web-ui run e2e`.
- Queries: browser loads `/` and the app consumes `/api/board`.
- API: no new runtime API.
- Tables: no new tables.
- Domain rules: E2E is read-only against the current repo board.
- UI surfaces: browser board and task detail panel.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Not primary. |
| Integration | Playwright starts the built local server. |
| E2E | Chromium verifies board and task detail UI. |
| Platform | Playwright Chromium installed and exercised locally. |
| Release | Not required. |

## Harness Delta

The browser proof gap from `US-049` is closed for the board/detail surface.
Full run/review/sync browser journey can be expanded later if the product needs
mutation-heavy E2E against disposable Harness fixtures.

## Evidence

- `npm --prefix crates/harness-symphony/web-ui exec playwright install chromium`
  installed Chromium.
- `npm --prefix crates/harness-symphony/web-ui run e2e` passed: 1 Chromium
  browser test.

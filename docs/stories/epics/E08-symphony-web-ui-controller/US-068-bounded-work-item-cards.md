# US-068 Bounded Work Item Cards

## Status

planned

## Lane

normal

## Product Contract

The Symphony Web UI board must keep work-item cards bounded inside their
six-state board columns. A card shows a compact summary on the board, while the
complete work-item content remains available from the task detail popup.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Acceptance Criteria

- Work-item cards never create horizontal scrolling inside a board column.
- Long task titles, reasons, run IDs, failure categories, lane labels, and
  blocker metadata wrap, clamp, or truncate within the card boundary.
- The board card remains a bounded summary; full work-item information is shown
  in the existing task detail popup.
- Dense task lists continue to scroll vertically inside columns on desktop and
  mobile.
- The six-column desktop board remains scannable and the mobile board remains
  usable.
- Existing board APIs, task state derivation, run actions, review actions, and
  sync behavior are unchanged.

## Design Notes

- Commands: `harness-symphony web`, Vite build, Playwright E2E.
- Queries: `GET /api/board`.
- API: no new API shape.
- Tables: no new tables.
- Domain rules: visual layout only; board state derivation remains backend-owned.
- UI surfaces: `crates/harness-symphony/web-ui` board columns, task cards, and
  task detail popup.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-068 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript build compiles the bounded card implementation. |
| Integration | Vite production build succeeds with the existing Web UI bundle. |
| E2E | Playwright uses long mocked work-item content and asserts no horizontal overflow at the page, board, column, and card levels on desktop and mobile. |
| Platform | Playwright screenshots or equivalent visual artifacts show dense desktop and mobile board states without clipped controls or horizontal card scroll. |
| Release | Not required. |

## Harness Delta

No durable Harness process change expected. This story should leave a validation
pattern that future Web UI stories can reuse for overflow-sensitive layouts.

## Evidence

Add commands, reports, screenshots, or links after validation exists.

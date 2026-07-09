# US-076 Run Ready Story From Board Card

## Status

implemented

## Lane

normal

## Product Contract

Let an operator start a Ready story directly from its board card through a
guarded Codex run action, without opening the detail popup first.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`
- `PRODUCT.md`

## Acceptance Criteria

- Ready cards show a `Run with Codex` action.
- The action asks for confirmation before starting Symphony.
- The action calls the existing `POST /api/tasks/<story-id>/start` endpoint.
- Starting from the card refreshes the board and moves the story toward `In Progress`.
- Clicking the direct run action does not open the task detail popup.
- The action is disabled when proof is missing or another run is active.

## Design Notes

- Commands: no new CLI command.
- Queries: board refresh after successful start.
- API: reuses `POST /api/tasks/<story-id>/start`.
- Tables: no schema changes.
- Domain rules: existing backend active-run and dependency guards remain authoritative.
- UI surfaces: Ready board cards.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-076 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript build succeeds. |
| Integration | Existing start endpoint remains unchanged. |
| E2E | `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "ready card runs"` |
| Platform | `npm --prefix crates/harness-symphony/web-ui run desktop:smoke --loglevel verbose` |
| Release | `npm --prefix crates/harness-symphony/web-ui run e2e`, `git diff --check` |

## Harness Delta

No Harness policy change expected.

## Evidence

Implemented direct Ready-card Codex run action.

- RED: `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "ready card runs"` failed before the card action existed.
- Targeted E2E: `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "ready card runs"` passed.
- Build: `npm --prefix crates/harness-symphony/web-ui run build` passed.
- Full E2E: `npm --prefix crates/harness-symphony/web-ui run e2e` passed 22 Chromium tests.
- Desktop smoke: `npm --prefix crates/harness-symphony/web-ui run desktop:smoke --loglevel verbose` passed.
- Design detector: `node .agents/skills/impeccable/scripts/detect.mjs --json crates/harness-symphony/web-ui/src crates/harness-symphony/web-ui/index.html` returned `[]`.
- Story verify: `scripts/bin/harness-cli story verify US-076` passed.
- Clean diff: `git diff --check` passed.

# US-073 Command Center Web UI Redesign

## Status

implemented

## Lane

normal

## Product Contract

Redesign the Symphony Web UI into a cleaner Command Center surface while preserving
the existing board-first workflow, task detail dialog, local-only API contract,
and one-active-run operating model.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`
- `crates/harness-symphony/web-ui/PRODUCT.md`
- `crates/harness-symphony/web-ui/DESIGN.md`

## Acceptance Criteria

- The first viewport reads as a Command Center, with a compact command bar,
  state overview, search, refresh, and six-state board visible.
- Existing task selection, detail dialog, recovery, review, delete, and sync
  controls keep their behavior and accessible names.
- Dense board columns remain internally scrollable with no page/card horizontal
  overflow on desktop or mobile.
- Visual styling uses local shadcn-style primitives and Tailwind utilities.

## Design Notes

- Commands: no new backend commands.
- Queries: no new API query shape.
- API: preserve existing `/api/board`, review, events, recovery, PR, and sync
  endpoints.
- Tables: no schema changes.
- Domain rules: no change to task states, dependencies, or active-run lock.
- UI surfaces: main shell, summary strip, board columns, task cards, sidebar,
  detail overlay polish.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-073 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript build succeeds. |
| Integration | React board/detail route renders against mocked API in Playwright. |
| E2E | `npm --prefix crates/harness-symphony/web-ui run e2e` passes. |
| Platform | `npm --prefix crates/harness-symphony/web-ui run desktop:smoke` passes. |
| Release | `cargo test --workspace`, `cargo fmt --check`, `cargo clippy --workspace -- -D warnings`, `git diff --check`. |

## Harness Delta

No harness policy change expected.

## Evidence

Implemented Command Center shell and board polish.

- RED: `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "board renders task columns"` failed on missing `Symphony Command Center` heading before implementation.
- Build: `npm --prefix crates/harness-symphony/web-ui run build`.
- E2E: `npm --prefix crates/harness-symphony/web-ui run e2e` passed 19 Chromium tests.
- Story verify: `scripts/bin/harness-cli story verify US-073` passed.
- Desktop platform smoke: `npm --prefix crates/harness-symphony/web-ui run desktop:smoke --loglevel verbose`.
- Design detector: `node .agents/skills/impeccable/scripts/detect.mjs --json crates/harness-symphony/web-ui/src crates/harness-symphony/web-ui/index.html` returned `[]`.
- Rust workspace: `cargo fmt --check`, `cargo test --workspace --quiet`, `cargo clippy --workspace -- -D warnings`.
- Clean diff: `git diff --check`.
- Browser proof: desktop and mobile screenshots captured in Codex browser after viewport reset.

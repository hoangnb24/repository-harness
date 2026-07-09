# US-074 Guided Intake Draft UI

## Status

implemented

## Lane

normal

## Product Contract

Add a draft-only Guided Intake surface to the Symphony Web UI so an operator can
turn a rough product idea into a reviewable story draft before any durable
Harness records or Symphony runs are created.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`
- `crates/harness-symphony/web-ui/PRODUCT.md`
- `crates/harness-symphony/web-ui/DESIGN.md`

## Acceptance Criteria

- A `Guided Intake` view is available from the Command Center shell.
- The view captures a rough idea and a short one-question-at-a-time intake flow.
- A live draft preview shows audience, outcome, non-goals, validation, and lane.
- The MVP does not create stories, write durable intake rows, or start Symphony.
- Existing board/detail behavior remains unchanged.

## Design Notes

- Commands: no new backend command.
- Queries: no new API query.
- API: no web API changes in this story.
- Tables: no schema changes.
- Domain rules: draft-only; source of truth remains existing Harness records.
- UI surfaces: Command Center view tabs, Guided Intake form, story preview.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-074 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript build succeeds. |
| Integration | React intake view renders and updates preview in Playwright. |
| E2E | `npm --prefix crates/harness-symphony/web-ui run e2e` passes. |
| Platform | `npm --prefix crates/harness-symphony/web-ui run desktop:smoke` passes. |
| Release | `cargo test --workspace`, `cargo fmt --check`, `cargo clippy --workspace -- -D warnings`, `git diff --check`. |

## Harness Delta

No Harness policy change expected. Future backend story should add guarded
durable writes only after explicit user confirmation.

## Evidence

Implemented draft-only Guided Intake UI.

- RED: `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "guided intake"` failed on missing `Guided Intake` tab before implementation.
- Build: `npm --prefix crates/harness-symphony/web-ui run build`.
- Targeted E2E: `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "guided intake"` passed.
- Full E2E: `npm --prefix crates/harness-symphony/web-ui run e2e` passed 20 Chromium tests.
- Story verify: `scripts/bin/harness-cli story verify US-074` passed.
- Desktop platform smoke: `npm --prefix crates/harness-symphony/web-ui run desktop:smoke --loglevel verbose`.
- Design detector: `node .agents/skills/impeccable/scripts/detect.mjs --json crates/harness-symphony/web-ui/src crates/harness-symphony/web-ui/index.html` returned `[]`.
- Rust workspace: `cargo fmt --check`, `cargo test --workspace --quiet`, `cargo clippy --workspace -- -D warnings`.
- Clean diff: `git diff --check`.
- Browser proof: Guided Intake view opened in Codex browser and screenshot captured.

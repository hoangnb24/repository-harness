# US-075 Create Story From Guided Intake

## Status

implemented

## Lane

normal

## Product Contract

Let an operator turn a completed Guided Intake draft into durable Harness
records from the Web UI after explicit confirmation, without starting Symphony.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`
- `PRODUCT.md`

## Acceptance Criteria

- Guided Intake shows a `Create story` action after rough idea, outcome, and validation proof are present.
- The action asks for confirmation before writing durable records.
- The backend writes one `intake` row and one planned `story` row.
- The created story carries the validation proof as `verify_command` and appears on the board after refresh.
- The flow does not call task start, create a run, create a PR, mutate dependencies, or sync changes.

## Design Notes

- Commands: no Symphony execution command is invoked.
- Queries: board refresh after successful create.
- API: `POST /api/intake` with `idea`, `audience`, `outcome`, `non_goals`, and `validation`.
- Tables: writes existing `intake` and `story` tables only.
- Domain rules: next story id uses the next numeric `US-XXX` id; non-numeric story ids are ignored.
- UI surfaces: Guided Intake preview action and board refresh.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-075 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `cargo test -p harness-symphony guided_intake -- --nocapture` |
| Integration | `npm --prefix crates/harness-symphony/web-ui run build` |
| E2E | `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "guided intake creates"` |
| Platform | `npm --prefix crates/harness-symphony/web-ui run desktop:smoke --loglevel verbose` |
| Release | `cargo test --workspace`, `cargo fmt --check`, `cargo clippy --workspace -- -D warnings`, `git diff --check` |

## Harness Delta

Guided Intake now has a guarded durable create path. It remains separate from
Symphony execution.

## Evidence

Implemented guarded story creation from Guided Intake.

- RED: `cargo test -p harness-symphony guided_intake -- --nocapture` failed before `POST /api/intake` existed.
- RED: `npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "guided intake creates"` failed before the create action existed.
- Targeted: `npm --prefix crates/harness-symphony/web-ui run build && npm --prefix crates/harness-symphony/web-ui run e2e -- --grep "guided intake" && cargo test -p harness-symphony guided_intake -- --nocapture` passed.
- Build: `npm --prefix crates/harness-symphony/web-ui run build` passed.
- Full E2E: `npm --prefix crates/harness-symphony/web-ui run e2e` passed 21 Chromium tests.
- Desktop smoke: `npm --prefix crates/harness-symphony/web-ui run desktop:smoke --loglevel verbose` passed.
- Design detector: `node .agents/skills/impeccable/scripts/detect.mjs --json crates/harness-symphony/web-ui/src crates/harness-symphony/web-ui/index.html` returned `[]`.
- Rust workspace: `cargo fmt --check`, `cargo test --workspace --quiet`, and `cargo clippy --workspace -- -D warnings` passed.
- Clean diff: `git diff --check` passed.
- Story verify: `scripts/bin/harness-cli story verify US-075` recorded `last_verified_result=pass` at `2026-07-09 04:42:50`.

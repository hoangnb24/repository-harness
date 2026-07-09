# Create Story From Guided Intake Design

## Direction

Extend Guided Intake from draft-only shaping into a guarded create flow. The UI
should make record creation explicit and keep Symphony execution separate.

## Scope

- Add a `Create story` action to the draft preview.
- Require rough idea, outcome, and validation proof before create.
- Confirm before durable writes.
- Add `POST /api/intake` to create one intake row and one planned story row.
- Refresh the board and filter to the created story.
- Do not start Symphony or mutate dependencies.

## Architecture

Keep draft state in the React intake component. `main.tsx` owns confirmation,
API call, board refresh, and view switch. Backend code uses the existing
`rusqlite` boundary in `work.rs` and the simple local HTTP router in `web.rs`.

## Validation

- RED: Playwright create test fails without the button/endpoint.
- RED: Rust web test fails without `POST /api/intake`.
- GREEN: targeted Rust and Playwright tests pass.
- Full proof: build, e2e, desktop smoke, detector, Rust workspace checks.

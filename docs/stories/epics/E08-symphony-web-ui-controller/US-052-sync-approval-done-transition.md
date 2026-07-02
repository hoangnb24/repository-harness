# US-052 Sync Approval And Done Transition

## Status

implemented

## Lane

high-risk

## Product Contract

After a reviewed PR is accepted, the Web UI must let the user approve Symphony
sync and then show the task as Done when the accepted changeset has been
applied locally.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Acceptance Criteria

- `POST /api/runs/<run-id>/sync` invokes the existing Symphony sync flow.
- Unknown run ids return JSON 404.
- Applied changesets mark the matching run `sync_status` as `synced`.
- The board derives Done for completed synced runs.
- The browser review panel exposes an Approve Sync action for completed reviewed
  runs.
- The UI refreshes the board after sync.

## Design Notes

- Commands: `harness-symphony web`; existing `harness-symphony sync`.
- Queries: `POST /api/runs/<run-id>/sync`.
- API: sync response lists applied/skipped changes and whether the selected run
  had a changeset applied.
- Tables: reuses `run_state` and `changeset_sync`.
- Domain rules: sync approval delegates to the existing idempotent changeset
  sync; it does not create a second apply path.
- UI surfaces: review panel Approve Sync button.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | State-store sync status update and sync/web route tests. |
| Integration | Existing sync tests plus web route safety checks. |
| E2E | Deferred to `US-053`. |
| Platform | TypeScript build proves Approve Sync UI compiles against the API contract. |
| Release | Not required. |

## Harness Delta

No process change.

## Evidence

- `scripts/bin/harness-cli story verify US-052` passed.
- `npm --prefix crates/harness-symphony/web-ui run build` passed.
- `cargo test --workspace` passed: 97 tests.
- `cargo fmt --check` passed.
- `cargo clippy --workspace -- -D warnings` passed.

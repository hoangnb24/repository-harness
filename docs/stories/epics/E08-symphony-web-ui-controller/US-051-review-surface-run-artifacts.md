# US-051 Review Surface For Run Artifacts

## Status

implemented

## Lane

high-risk

## Product Contract

The Web UI review surface must expose enough information for a user to make an
approval decision without leaving the local controller. It must read existing
Symphony artifacts rather than creating another review store.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Acceptance Criteria

- Board API items expose the latest run id for reviewable tasks.
- `GET /api/runs/<run-id>/review` returns run status, outcome, summary,
  `RESULT.json`, validation evidence, changed files, rendered changeset
  preview, PR URL/status, raw artifact paths, recent events, and suggested next
  action.
- Missing run ids return JSON 404.
- The browser task detail panel displays the review payload for Review, Needs
  Attention, and Done tasks.
- The review surface does not mutate run state or create PRs.

## Design Notes

- Commands: `harness-symphony web`.
- Queries: `GET /api/runs/<run-id>/review`.
- API: review response is read-only and backed by `.harness/runs`,
  `.harness/changesets`, and `.symphony/state.db`.
- Tables: reuses `run_state`.
- Domain rules: PR merge status remains `created` or `missing` until the sync
  approval story adds merge/sync actions.
- UI surfaces: task detail review panel.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Web route test returns review artifact payload and changeset preview. |
| Integration | Review test reads real fixture `SUMMARY.md`, `RESULT.json`, changeset, PR URL, and event log. |
| E2E | Deferred to `US-053`. |
| Platform | TypeScript build proves the browser panel compiles against the API contract. |
| Release | Not required. |

## Harness Delta

No process change.

## Evidence

- `cargo test -p harness-symphony web -- --nocapture` passed: 10 web tests,
  including review artifact fixture coverage.
- `npm --prefix crates/harness-symphony/web-ui run build` passed.
- `cargo test --workspace` passed: 95 tests.
- `cargo fmt --check` passed.
- `cargo clippy --workspace -- -D warnings` passed.

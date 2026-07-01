# US-067 Per-Run Agent Selection From the Board

## Status

implemented

## Lane

normal

## Product Contract

When more than one agent is set up, a run can be launched with a chosen agent
instead of only the globally configured one.

Agent selection was previously a single global setting (`agent.adapter`); every
run used it. This story adds a per-run override at launch time: the board's task
detail offers an agent picker (the Ready agents, defaulting to the active one),
and starting the task runs it with the selected agent. The global
`agent.adapter` remains the default when no override is given. Nothing is stored
on the ticket — the choice is per-run.

## Relevant Product Docs

- `docs/stories/US-065-agent-setup-status-surface.md` (the readiness data reused
  by the picker)
- `docs/stories/US-064-first-class-symphony-claudecode-adapter.md`

## Acceptance Criteria

- `POST /api/tasks/<id>/start` accepts an optional `?adapter=<name>` override.
- An unknown adapter is rejected with 400; a known adapter (`custom`, `codex`,
  `claudecode`) is accepted and used for that run.
- A named-adapter override resolves its own default command; only `custom`
  keeps the globally configured `agent.command`.
- With no `adapter`, the run uses the global `agent.adapter` exactly as before.
- The task detail shows an agent dropdown listing only Ready agents, defaulting
  to the active adapter; Start launches the run with the selected agent.

## Design Notes

- Backend: `crates/harness-symphony/src/web.rs` — `start_adapter_override`
  parses the query; `config_with_adapter` clones the resolved config with the
  chosen adapter; `start_run_response` runs `prepare_run`/`spawn_run` with that
  per-run config. `start_path_story_id` now tolerates a query string.
- Frontend: `crates/harness-symphony/web-ui/src/main.tsx` — `TaskDetail` takes
  the `agents` list, renders the picker (Ready agents, active default), and
  `startTask` appends `?adapter=`.
- No schema change and no change to the run contract, result validation, or
  changeset flow — the override only chooses which adapter `run_agent` invokes.
- Future (not in scope): a durable per-ticket preferred agent (a `story` column)
  would build on this by seeding the picker's default.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-067 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `start_adapter_override` query parsing; `config_with_adapter` override + unknown-adapter rejection + custom command retention. |
| Integration | Live `POST /start?adapter=bogus` -> 400; `?adapter=codex` -> 202 and produces the codex event log. |
| E2E | Task detail renders the agent picker with Ready agents; agents strip unaffected. |
| Platform | UI builds (tsc + vite). |
| Release | Workspace tests, fmt, clippy. |

## Evidence

- `cargo test -p harness-symphony` — 90 passed (+3 new); the 2 failures are the
  pre-existing git-2.28 `pr::tests`. `clippy -D warnings` and `fmt --check`
  clean; `npm run build` clean; agents e2e 2 passed.
- Live: `?adapter=bogus` returned 400 with the supported-adapter list;
  `?adapter=codex` started a run whose worktree produced
  `APP_SERVER_EVENTS.jsonl` (codex), confirming the override selected codex over
  the global `claudecode`.

## Harness Delta

Turns the multi-agent readiness surface into actual routing: with several agents
ready, each run can pick which one executes it, without changing the durable run
pipeline.

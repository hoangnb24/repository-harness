# US-064 First-Class Symphony Claude Code Adapter

## Status

implemented

## Lane

normal

## Product Contract

Symphony treats Claude Code as a named agent adapter (`claudecode`) alongside
`codex` and `custom`, so users do not have to wire the `claude` CLI through the
generic custom command adapter.

The `claudecode` adapter drives Claude Code headless: it launches
`claude -p <prompt> --output-format stream-json --verbose
--dangerously-skip-permissions` (adding `--model <m>` when `agent.model` is set)
inside the prepared worktree, streams events to `CLAUDE_CODE_EVENTS.jsonl`, and
treats the terminal `{"type":"result",...}` event as the authoritative success
signal before Symphony's existing result validation runs.

Because agent selection is meaningless without a working agent, the change also
adds an agent-readiness engine: for each adapter Symphony reports binary
presence and a heuristic (no-network) auth check, surfaced through a new
`doctor` row and (US-065) the Web UI.

The `custom` and `codex` adapters keep their existing behavior.

## Relevant Product Docs

- `docs/SYMPHONY_SCOPE.md` (sections 4.5, 9, 12.3)
- `docs/SYMPHONY_QUICKSTART.md` (Agent Prerequisites)
- `docs/stories/US-046-first-class-symphony-codex-adapter.md`

## Acceptance Criteria

- `agent.adapter: claudecode` is accepted and defaults its command to `claude`
  without requiring an explicit `agent.command`.
- The adapter injects the shared run prompt via `-p` and requests stream-json
  output, running one-shot to process exit (not a persistent server).
- Completion detection is faithful: the terminal `result` event's `is_error`
  decides success; a run that exits without ever emitting a result event is an
  error, not a silent success.
- A run cannot be misreported: the final stdout line is drained race-free, and
  stderr is drained continuously so a chatty CLI cannot stall the run.
- `agent.model` is an optional config field, threaded into `ResolvedConfig` and
  shown in `config show`.
- `doctor` reports an `agent prerequisites` row for the active adapter
  (binary + heuristic auth), warning (never failing) when a prerequisite is
  unconfirmed, with an actionable next step.
- `agent.adapter: codex` and `agent.adapter: custom` are unchanged; unsupported
  adapters fail with an actionable error listing `custom, codex, claudecode`.

## Design Notes

- Adapter boundary: `crates/harness-symphony/src/agent.rs`
  (`run_claude_code_agent`, `claude_code_args`, `record_claude_line`).
- Readiness engine: pure `resolve_readiness` + thin `probe_binary` (5s timeout)
  / `probe_auth` gatherers; `agent_readiness` / `all_agent_readiness`.
- Config: `agent.model` in `src/config.rs`; `agent_model` on `ResolvedConfig`.
- Doctor row: `check_agent_prerequisites` in `src/doctor.rs`, inserted after the
  untouched `check_agent_adapter`.
- `codex_prompt` was renamed to `agent_prompt` (it is agent-agnostic) and shared
  by both named adapters. `run_codex_agent` was left unchanged.
- Follow-up: `run_codex_agent` shares the older single-thread stderr pattern; a
  backlog item tracks draining its stderr the same way.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-064 --unit 1 --integration 1 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Adapter command defaults, `claude_code_args` model flag on/off, readiness mapping across all branches, config propagation. |
| Integration | Fake `claude` scripts: success result, error result, and no-result-event (all via stream-json over stdout). |
| E2E | Live `claude -p` run can be exercised separately once credentials are configured on the host. |
| Platform | `doctor` recognizes the adapter and reports prerequisites on the local platform. |
| Release | Workspace tests, fmt, clippy. |

## Evidence

- `cargo test -p harness-symphony` — 85 passed; the only 2 failures are the
  pre-existing `pr::tests` cases that need git >= 2.28 (`git init -b main`).
- `cargo clippy -p harness-symphony -- -D warnings` — clean.
- `cargo fmt --check` — clean.
- `cargo run -q -p harness-symphony -- doctor` — shows the `agent prerequisites`
  row (detected `claude 2.1.197`; auth warned as unconfirmed with next step).
- `cargo run -q -p harness-symphony -- config show` — prints `agent_model`.

## Harness Delta

This story proves the `agent.adapter` extension point with a second protocol
shape (one-shot streaming vs. Codex's persistent JSON-RPC) and adds the
readiness surface that US-065 renders in the Web UI.

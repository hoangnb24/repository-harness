# US-066 Claude Code Login Detection and Nested-Session Safety

## Status

implemented

## Lane

normal (change request refining US-064 readiness/adapter behavior)

## Product Contract

An installed and logged-in Claude Code is detected as ready and is usable by the
harness without extra configuration.

Before this change the `claudecode` auth check only recognized an
`ANTHROPIC_API_KEY` env var, a `~/.claude/.credentials.json` file, or Bedrock/
Vertex vars. A normal interactive `claude` login stores its OAuth token outside
those locations (e.g. the OS keychain), so a fully working, logged-in CLI was
reported as `needs-setup`. This story closes that gap and hardens spawning.

Three additions:

1. **Login detection** — the auth check also treats a completed login recorded
   in `~/.claude.json` (an `oauthAccount` object or a non-empty `userID`) as
   authenticated. The token itself is never read.
2. **Binary override** — the `claudecode` binary resolves an explicit
   `CLAUDE_EXECUTABLE` path (tilde-expanded) before falling back to `claude` on
   `PATH`.
3. **Nested-session safety** — when the harness runs inside a Claude Code
   session, the spawned agent has the inherited `CLAUDECODE` and
   `CLAUDE_CODE_CHILD_SESSION` flags removed so it starts as a clean top-level
   session.

## Relevant Product Docs

- `docs/SYMPHONY_QUICKSTART.md` (Agent Prerequisites)
- `docs/stories/US-064-first-class-symphony-claudecode-adapter.md`
- `docs/stories/epics/E08-symphony-web-ui-controller/US-065-agent-setup-status-surface.md`

## Acceptance Criteria

- A machine with `claude` installed and logged in reports `claudecode` as
  `ready` in both `doctor` and the Web UI `Agents` strip.
- The auth detail names the signal that matched (e.g. "logged in via Claude
  Code (~/.claude.json)").
- `CLAUDE_EXECUTABLE`, when set to an existing file, is used as the Claude
  binary; otherwise `claude` on `PATH` is used and existing defaults are
  unchanged.
- A `claudecode` run started from inside a Claude Code session does not inherit
  the nested-session flags.
- No secrets are read or logged; only the presence of login markers is checked.

## Design Notes

- All changes are in `crates/harness-symphony/src/agent.rs`:
  `config_indicates_login` (pure) + `claude_config_login` gatherer feed
  `probe_auth`; `resolve_claude_binary` + `expand_tilde` feed
  `resolved_agent_command` and `agent_binary_name`; `run_claude_code_agent`
  strips the nested-session env vars.
- Decision logic stays pure and unit-tested; environment/file reads stay thin.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-066 --unit 1 --integration 0 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `config_indicates_login` across oauthAccount / userID / empty; `expand_tilde` home-prefix rules. |
| E2E | Web UI `Agents` strip shows `claudecode` as Ready on a logged-in host. |
| Platform | `doctor` reports the `agent prerequisites` row as pass on the local platform. |
| Release | Workspace tests, fmt, clippy. |

## Evidence

- `cargo test -p harness-symphony` — 88 passed (the 2 failures are the
  pre-existing git-2.28 `pr::tests`); `cargo clippy -p harness-symphony -- -D
  warnings` and `cargo fmt --check` clean.
- Live `doctor` with `adapter: claudecode` — `agent prerequisites` PASS,
  `auth: logged in via Claude Code (~/.claude.json)`.
- Web UI `Agents` strip renders `claudecode` as Ready in the browser.

## Harness Delta

Makes the readiness surface trustworthy for the common case (an interactively
logged-in Claude Code) and keeps a spawned agent isolated from the harness's own
session.

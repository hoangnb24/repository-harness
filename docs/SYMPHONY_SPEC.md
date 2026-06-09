# Harness Symphony Service Specification

Status: Draft v2 (language-agnostic, post-audit revision)

Purpose: Define a headless daemon service that dispatches coding agent sessions
against work items from pluggable sources, running agents in a Harness-governed
repository where the agent follows the Harness protocol autonomously.

## Normative Language

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`,
`RECOMMENDED`, `MAY`, and `OPTIONAL` in this document are to be interpreted as
described in RFC 2119.

`Implementation-defined` means the behavior is part of the implementation
contract, but this specification does not prescribe one universal policy.
Implementations MUST document the selected behavior.

## 1. Problem Statement

Harness Symphony is a long-running headless daemon that reads work from a
pluggable source (issue tracker, Harness backlog, or command queue), launches
Codex agent sessions in a Harness-governed repository, and monitors their
lifecycle.

The service solves three operational problems:

- It turns agent execution into a repeatable daemon workflow instead of manual
  sessions.
- It keeps the workflow policy in-repo (`WORKFLOW.md`) so teams version
  scheduling config alongside their code and Harness docs.
- It provides enough observability to operate and debug agent runs (structured
  logs, optional TUI dashboard).

Important boundaries:

- Symphony is a **scheduler and runner**. It launches agents and monitors
  liveness. It does NOT classify work, assemble context, score traces, or run
  verification gates — the agent does all of that by following the Harness
  protocol (`AGENTS.md`, `FEATURE_INTAKE.md`, `CONTEXT_RULES.md`, etc.).
- Ticket writes (state transitions, comments, PR links) are performed by the
  coding agent using tools available in its session.
- A successful run can end at a workflow-defined handoff state (for example
  `Human Review`), not necessarily `Done`.
- The Harness context layer (docs, templates, CLI, `harness.db`) is the
  agent's operating environment. Symphony does not replace or enforce
  Harness — it orchestrates work within a Harness-governed repo.

### 1.1 Relationship to Harness

Harness is a repo-level operating system for coding agents. It provides:

- Feature intake classification and work generation
  (`docs/FEATURE_INTAKE.md`)
- Phase-by-lane context rules (`docs/CONTEXT_RULES.md`)
- Durable operational memory (`harness.db` via `harness-cli`)
- Story lifecycle, verification gates, trace recording
- Friction capture and improvement proposals

**All of these are agent-side responsibilities.** The agent follows Harness
because the repository's docs tell it to — not because an orchestrator
forces it. This is Harness's core design philosophy:

> "Coding agents need better repositories, not better orchestrators."

Symphony's role is to get the agent into the repo and keep it running.
Everything inside the session is governed by Harness docs, not by Symphony.

### 1.2 Relationship to OpenAI Symphony

This spec is derived from the OpenAI Symphony Service Specification (v1). Key
differences:

| Concern | Original Symphony | Harness Symphony |
|---|---|---|
| Work source | Linear only | Pluggable adapter (Linear first) |
| Agent awareness | None (black-box subprocess) | None (agent follows Harness autonomously) |
| Workspace model | Per-issue isolated directory | Single repo clone (v1); per-issue later |
| Persistent state | None (in-memory only) | None (in-memory; Harness has its own db) |
| Intake/context | Not applicable | Agent-side (not orchestrator) |
| Form factor | Headless daemon + optional HTTP | Headless daemon → optional TUI → optional HTTP |
| Concurrency | Up to 100+ agents, SSH workers | Single agent (v1); concurrency later |

Sections inherited from the original spec are noted with `[Symphony §N]`
references.

## 2. Goals and Non-Goals

### 2.1 Goals

- Read work items from a pluggable source on a fixed cadence.
- Maintain a single authoritative in-memory orchestrator state for dispatch,
  retries, and reconciliation.
- Launch Codex agent sessions in the Harness-governed repository with a
  rendered prompt containing the work item context.
- Stop active runs when work item state changes make them ineligible.
- Recover from transient failures with exponential backoff.
- Load runtime behavior from a repository-owned `WORKFLOW.md` contract.
- Expose operator-visible observability (structured logs at minimum).
- Support two intake modes: inline (agent handles intake as first step) and
  dedicated (separate intake session decomposes complex inputs into stories
  before dispatch).

### 2.2 Non-Goals

- Rich web UI or multi-tenant control plane.
- General-purpose workflow engine or distributed job scheduler.
- Built-in business logic for how to edit tickets, PRs, or comments (that
  logic lives in the workflow prompt and agent tooling).
- Orchestrator-side intake classification, context assembly, trace scoring,
  or verification gates — these are agent responsibilities governed by
  Harness docs.
- Multi-agent concurrency and shared-state management (deferred to v2).
- Replacing the Harness CLI or durable layer.
- Mandating a single sandbox or approval posture for all implementations.

## 3. Architecture Overview

### 3.1 Five-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HARNESS SYMPHONY                       │
│                                                           │
│  Layer 1: Work Source (pluggable)                         │
│    Reads work items from Linear, GitHub, harness.db, etc. │
│                                                           │
│  Layer 2: Intake Router                                   │
│    Simple tasks → dispatch directly (inline intake)       │
│    Complex tasks → dedicated intake session first         │
│                                                           │
│  Layer 3: Scheduler (daemon core)                         │
│    Poll loop, dispatch, retry, reconciliation, liveness   │
│                                                           │
│  Layer 4: Agent Runner (Codex)                            │
│    Launch Codex app-server, stream events, manage session │
│                                                           │
│  Layer 5: Harness Repo (execution environment)            │
│    Agent follows AGENTS.md → intake → context → work →    │
│    trace → verify → friction                              │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Main Components

1. `Workflow Loader`
   - Reads `WORKFLOW.md`.
   - Parses YAML front matter and prompt body.
   - Returns `{config, prompt_template}`.

2. `Config Layer`
   - Exposes typed getters for workflow config values.
   - Applies defaults and environment variable indirection.
   - Performs validation before dispatch.

3. `Work Source Adapter` (pluggable)
   - Fetches candidate work items from a configured source.
   - Fetches current states for specific item IDs (reconciliation).
   - Normalizes source payloads into a stable work item model.
   - Implementations: `LinearAdapter`, future `GitHubAdapter`,
     `HarnessBacklogAdapter`.

4. `Intake Router`
   - Examines each incoming work item.
   - Simple items (spec_slice, change_request, maintenance,
     harness_improvement) → dispatch directly; agent does inline intake.
   - Complex items (new_spec, new_initiative) → dispatch a dedicated intake
     session; generated stories become new dispatchable items.
   - Routing rules are configurable in `WORKFLOW.md`.

5. `Orchestrator`
   - Owns the poll tick.
   - Owns the in-memory runtime state.
   - Decides which items to dispatch, retry, stop, or release.
   - Single-agent dispatch in v1 (one running session at a time).

6. `Agent Runner`
   - Builds prompt from work item + workflow template.
   - Launches the Codex app-server subprocess in the repo directory.
   - Streams agent events back to the orchestrator.
   - Manages session lifecycle (turns, timeouts, continuation).

7. `Logging`
   - Emits structured runtime logs to configured sinks.

8. `Status Surface` (OPTIONAL, future)
   - TUI dashboard for real-time operator visibility.
   - HTTP API for programmatic access.

### 3.3 External Dependencies

- Work source API (Linear for `source.kind: linear` in v1).
- Local filesystem with the Harness-governed repository cloned.
- Codex app-server executable.
- Host environment authentication for the work source and Codex.

### 3.4 What Symphony Does NOT Own

These responsibilities belong to the agent following Harness docs:

| Responsibility | Harness Owner | Agent Reads |
|---|---|---|
| Intake classification | `FEATURE_INTAKE.md` | Agent classifies input type + risk lane |
| Work generation | `FEATURE_INTAKE.md` | Agent creates stories, epics, docs |
| Context assembly | `CONTEXT_RULES.md` | Agent loads phase-by-lane docs |
| Trace recording | `TRACE_SPEC.md` | Agent runs `harness-cli trace` |
| Verification | Story packets | Agent runs `harness-cli story verify` |
| Friction capture | `HARNESS.md` | Agent runs `harness-cli backlog add` |
| Decision recording | `HARNESS.md` | Agent runs `harness-cli decision add` |

Symphony observes outcomes (agent exit code, session events) but does not
participate in any of these processes.

## 4. Project Structure and Build Strategy

Symphony lives inside the `repository-harness` monorepo as an optional Cargo
workspace crate. This keeps the spec, CLI, and daemon in a single versioned
unit while allowing teams that don't need orchestration to skip it entirely.

### 4.1 Crate Layout

```
repository-harness/
  crates/
    harness-core/              ← shared library (types, db access, config)
      src/
        lib.rs
        db.rs                  ← harness.db reader (rusqlite)
        types.rs               ← WorkItem, IntakeRecord, TraceRecord, etc.
        config.rs              ← WORKFLOW.md parser, typed config
    harness-cli/               ← existing CLI binary
      src/
        main.rs
      Cargo.toml               ← depends on harness-core
    harness-symphony/          ← daemon binary (optional)
      src/
        main.rs                ← CLI entry (start, --tui, --port)
        orchestrator.rs        ← poll loop, dispatch, reconciliation
        source/
          mod.rs               ← WorkSource trait
          linear.rs            ← Linear adapter
        intake_router.rs       ← inline vs dedicated routing
        agent_runner.rs        ← Codex app-server client
        session.rs             ← live session tracking
      Cargo.toml               ← depends on harness-core
  scripts/bin/
    harness-cli                ← always shipped
    harness-symphony           ← shipped when built with symphony feature
  Cargo.toml                   ← workspace root
```

### 4.2 Dependency Graph

```
harness-symphony ──→ harness-core ←── harness-cli
       │                   │
       │                   ├── rusqlite (harness.db access)
       │                   └── serde, serde_yaml (config/types)
       │
       ├── tokio (async runtime, poll loop, timers)
       ├── reqwest (Linear API, future HTTP adapters)
       └── ratatui (optional, TUI dashboard)
```

`harness-core` is the shared library that both CLI and Symphony depend on.
It contains the types, database access, and config parsing that both need.
This prevents Symphony from reimplementing harness.db reading or duplicating
type definitions.

### 4.3 Feature Gating

The workspace `Cargo.toml` uses a feature flag so Symphony is opt-in:

```toml
[workspace]
members = ["crates/harness-core", "crates/harness-cli", "crates/harness-symphony"]
default-members = ["crates/harness-core", "crates/harness-cli"]
```

Build commands:

```bash
# Standard build (CLI only, no Symphony)
cargo build --release

# Full build (CLI + Symphony)
cargo build --release --workspace

# Symphony only
cargo build --release -p harness-symphony
```

### 4.4 Installation

The existing `scripts/install-harness.sh` gains an optional flag:

```bash
# Standard install (CLI + docs + templates)
./scripts/install-harness.sh

# Full install (CLI + docs + templates + Symphony daemon)
./scripts/install-harness.sh --with-symphony
```

When `--with-symphony` is passed, the installer also copies
`harness-symphony` to `scripts/bin/` and creates an example
`WORKFLOW.md` if one does not exist.

### 4.5 Future Extraction

If Symphony outgrows the monorepo (different release cadence, much larger
dependency tree, separate team), extracting it is straightforward:

1. Move `crates/harness-symphony/` to a new repo.
2. Point its `Cargo.toml` at `harness-core` as a git dependency.
3. The spec remains in `repository-harness/docs/SYMPHONY_SPEC.md` as the
   contract.

This is a one-way door that can be opened later — no need to decide now.

## 5. Core Domain Model

### 5.1 Entities

#### 5.1.1 Work Item

Normalized work record used by scheduling, prompt rendering, and observability.

Fields:

- `id` (string) — Stable source-internal ID.
- `identifier` (string) — Human-readable key (e.g., `MT-42`, `US-015`).
- `title` (string)
- `description` (string or null)
- `priority` (integer or null) — Lower = higher priority.
- `state` (string) — Current source state name.
- `source_kind` (string) — Which adapter produced this item.
- `labels` (list of strings) — Normalized to lowercase.
- `blocked_by` (list of blocker refs)
- `url` (string or null) — Link back to source.
- `intake_hint` (string or null) — OPTIONAL hint for intake routing
  (`inline` or `dedicated`). Source adapters MAY set this based on labels
  or item metadata.
- `created_at` (timestamp or null)
- `updated_at` (timestamp or null)

#### 5.1.2 Workflow Definition

Parsed `WORKFLOW.md` payload:

- `config` (map) — YAML front matter root object.
- `prompt_template` (string) — Markdown body after front matter, trimmed.

#### 5.1.3 Service Config (Typed View)

Typed runtime values derived from `WorkflowDefinition.config` plus environment
resolution. See Section 6.3 for the full schema.

#### 5.1.4 Run Attempt

One execution attempt for one work item.

Fields:

- `item_id`
- `item_identifier`
- `attempt` (integer or null — `null` for first run, `>=1` for retries)
- `mode` (`inline` | `intake`) — Whether this is an inline execution or a
  dedicated intake session.
- `started_at`
- `status`
- `error` (OPTIONAL)

#### 5.1.5 Live Session (Agent Session Metadata)

State tracked while a Codex subprocess is running:

- `session_id` (string, `<thread_id>-<turn_id>`)
- `thread_id`, `turn_id` (strings)
- `codex_app_server_pid` (string or null)
- `last_codex_event` (string or null)
- `last_codex_timestamp` (timestamp or null)
- `last_codex_message` (string)
- `codex_input_tokens`, `codex_output_tokens`, `codex_total_tokens` (integers)
- `turn_count` (integer)

#### 5.1.6 Retry Entry

- `item_id`
- `identifier`
- `attempt` (integer, 1-based)
- `due_at_ms` (monotonic timestamp)
- `timer_handle`
- `error` (string or null)

#### 5.1.7 Orchestrator Runtime State

Single authoritative in-memory state:

- `poll_interval_ms`
- `running` (map `item_id -> running entry`) — v1: at most one entry.
- `claimed` (set of item IDs)
- `retry_attempts` (map `item_id -> RetryEntry`)
- `completed` (set of item IDs, bookkeeping only)
- `codex_totals` (aggregate tokens + runtime seconds)

### 5.2 Stable Identifiers

- `Item ID` — Use for source lookups and internal map keys.
- `Item Identifier` — Use for human-readable logs.
- `Session ID` — `<thread_id>-<turn_id>`.

## 6. Workflow Specification (Repository Contract)

### 6.1 File Discovery

Workflow file path precedence:

1. Explicit CLI argument.
2. Default: `WORKFLOW.md` in the current working directory.

If the file cannot be read, return `missing_workflow_file` error.

### 6.2 File Format

`WORKFLOW.md` is a Markdown file with OPTIONAL YAML front matter.

Parsing rules (identical to [Symphony §5.2]):

- If file starts with `---`, parse until next `---` as YAML.
- Remaining lines become the prompt body.
- YAML front matter MUST decode to a map.
- Prompt body is trimmed.

### 6.3 Front Matter Schema

Top-level keys:

- `source` — Work source configuration (replaces `tracker` from original).
- `polling`
- `agent`
- `codex`
- `hooks`
- `intake`

Unknown keys SHOULD be ignored for forward compatibility.

#### 6.3.1 `source` (object)

Fields:

- `kind` (string, REQUIRED) — Work source adapter. Supported: `linear`.
  Future: `github`, `harness_backlog`.
- `endpoint` (string) — API endpoint.
  Default for `linear`: `https://api.linear.app/graphql`.
- `api_key` (string) — MAY be `$VAR_NAME` for environment indirection.
- `project_slug` (string) — REQUIRED when `kind == linear`.
- `required_labels` (list of strings) — Default: `[]`.
- `active_states` (list of strings) — Default: `["Todo", "In Progress"]`.
- `terminal_states` (list of strings) —
  Default: `["Closed", "Cancelled", "Canceled", "Duplicate", "Done"]`.

#### 6.3.2 `polling` (object)

- `interval_ms` (integer) — Default: `30000`.

#### 6.3.3 `agent` (object)

- `max_turns` (positive integer) — Default: `20`.
- `max_retry_backoff_ms` (integer) — Default: `300000` (5 minutes).

Note: `max_concurrent_agents` is omitted in v1 (single agent). It will be
added when concurrency support is introduced.

#### 6.3.4 `codex` (object)

- `command` (string) — Default: `codex app-server`.
- `approval_policy` — Implementation-defined.
- `turn_timeout_ms` (integer) — Default: `3600000` (1 hour).
- `read_timeout_ms` (integer) — Default: `5000`.
- `stall_timeout_ms` (integer) — Default: `300000` (5 minutes).

#### 6.3.5 `hooks` (object)

- `before_run` (shell script string, OPTIONAL) — Runs before each attempt.
- `after_run` (shell script string, OPTIONAL) — Runs after each attempt.
- `timeout_ms` (integer) — Default: `60000`.

Note: `after_create` and `before_remove` from original Symphony are omitted
because v1 does not create per-issue workspaces.

#### 6.3.6 `intake` (object)

- `dedicated_types` (list of strings) —
  Default: `["new_spec", "new_initiative"]`.
  Work items matching these input type labels receive a dedicated intake
  session before execution dispatch.
- `inline_types` (list of strings) —
  Default: `["spec_slice", "change_request", "maintenance_request",
  "harness_improvement"]`.
  Work items matching these are dispatched directly; the agent handles
  intake as its first step.
- `default_mode` (string) — `inline` | `dedicated`. Default: `inline`.
  Used when a work item doesn't match either list.

### 6.4 Prompt Template Contract

The Markdown body of `WORKFLOW.md` is the per-item prompt template.

Rendering requirements (identical to [Symphony §5.4]):

- Strict template engine (Liquid-compatible).
- Unknown variables MUST fail rendering.

Template input variables:

- `item` (object) — All normalized work item fields.
- `attempt` (integer or null) — `null` on first attempt.
- `mode` (string) — `inline` or `intake`.

RECOMMENDED prompt structure:

```markdown
You are working on {{ item.identifier }}: {{ item.title }}.

Follow AGENTS.md in this repository. It will direct you to the Harness
operating docs (FEATURE_INTAKE.md, CONTEXT_RULES.md, HARNESS.md, etc.).

{% if mode == "intake" %}
This is a DEDICATED INTAKE session. Your job is to:
1. Read FEATURE_INTAKE.md and classify this input.
2. Generate the appropriate work artifacts (stories, epics, product docs).
3. Record the intake via harness-cli.
4. Do NOT implement — only decompose and plan.
{% endif %}

{% if item.description %}
## Description

{{ item.description }}
{% endif %}

{% if attempt %}
This is retry attempt {{ attempt }}. Check your previous work and continue.
{% endif %}
```

### 6.5 Dynamic Reload

REQUIRED (identical to [Symphony §6.2]):

- Detect `WORKFLOW.md` changes and re-apply without restart.
- Invalid reloads keep last known good config and emit an error.

## 7. Work Source Adapter Contract

### 7.1 Adapter Interface

Every work source adapter MUST implement:

1. `fetch_candidates()` → list of WorkItem
   - Returns items in dispatchable states.
2. `fetch_states_by_ids(ids)` → list of WorkItem (minimal)
   - Used for reconciliation.
3. `fetch_terminal_items()` → list of WorkItem
   - Used for startup cleanup (if applicable).

### 7.2 Linear Adapter

The Linear adapter follows the original Symphony's tracker integration
contract [Symphony §11]:

- GraphQL endpoint, `Authorization` header, `project_slug` filter.
- Pagination REQUIRED, page size default 50.
- Normalization: labels lowercased, blockers from inverse `blocks` relations,
  priority as integer, timestamps parsed from ISO-8601.
- Candidate query filters by `active_states` and `required_labels`.

### 7.3 Future Adapters

- `GitHubAdapter` — Read from GitHub Issues/Projects.
- `HarnessBacklogAdapter` — Read dispatchable stories and accepted backlog
  items from `harness.db` via `harness-cli query`.

These are NOT specified in v1 but the adapter interface MUST be designed to
accommodate them.

### 7.4 Error Handling

- Candidate fetch failure → skip dispatch for this tick.
- State refresh failure → keep running agents, retry next tick.
- Terminal fetch failure → log warning, continue startup.

## 8. Intake Router

### 8.1 Purpose

The intake router examines each candidate work item and decides whether it
should be dispatched directly (inline intake) or requires a dedicated intake
session first (for complex inputs that generate multiple stories).

### 8.2 Routing Logic

```text
function route_intake(item, config):
  if item.intake_hint is not null:
    return item.intake_hint  // source adapter override

  if any label in item.labels matches config.intake.dedicated_types:
    return "dedicated"

  if any label in item.labels matches config.intake.inline_types:
    return "inline"

  return config.intake.default_mode
```

### 8.3 Dedicated Intake Sessions

When a work item is routed to `dedicated` mode:

1. Symphony launches a Codex session with `mode: "intake"` in the prompt
   template variables.
2. The prompt instructs the agent to ONLY do intake (classify, generate
   stories, record intake) — not implement.
3. The agent reads `FEATURE_INTAKE.md`, classifies the input type, runs the
   risk checklist, and generates work artifacts (story packets, epic folders,
   product docs).
4. The agent records the intake via `harness-cli intake`.
5. Generated stories are written to `docs/stories/` in the repo.
6. On the next poll cycle, if a `HarnessBacklogAdapter` is configured, new
   stories become dispatchable work items. Otherwise, the operator manually
   creates tracker tickets for generated stories.

### 8.4 Inline Intake

When a work item is routed to `inline` mode:

1. Symphony launches a Codex session with `mode: "inline"`.
2. The agent does intake as its first step (classify, record, then work).
3. This is the default Harness model — one session handles everything.

## 9. Orchestrator State Machine

### 9.1 Work Item Orchestration States

Internal claim states (not tracker states):

1. `Unclaimed` — Not running, no retry scheduled.
2. `Claimed` — Reserved to prevent duplicate dispatch.
3. `Running` — Worker task exists.
4. `RetryQueued` — Retry timer pending.
5. `Released` — Claim removed (terminal, ineligible, or retries exhausted).

### 9.2 Run Attempt Lifecycle

1. `BuildingPrompt`
2. `LaunchingAgent`
3. `InitializingSession`
4. `StreamingTurn`
5. `Finishing`
6. `Succeeded`
7. `Failed`
8. `TimedOut`
9. `Stalled`
10. `CanceledByReconciliation`

### 9.3 Transition Triggers

Identical semantics to [Symphony §7.3]:

- `Poll Tick` → reconcile, validate, fetch, dispatch.
- `Worker Exit (normal)` → schedule continuation retry.
- `Worker Exit (abnormal)` → schedule exponential-backoff retry.
- `Codex Update Event` → update session metadata.
- `Retry Timer Fired` → re-check eligibility, re-dispatch or release.
- `Reconciliation Refresh` → stop runs whose items are terminal/inactive.
- `Stall Timeout` → kill worker, schedule retry.

## 10. Polling, Scheduling, and Reconciliation

### 10.1 Poll Loop

At startup: validate config, schedule immediate tick, repeat every
`polling.interval_ms`.

Tick sequence:

1. Reconcile running items (stall detection + state refresh).
2. Validate dispatch config.
3. Fetch candidates from work source adapter.
4. Route each candidate through the intake router.
5. Dispatch eligible items while slots remain (v1: 1 slot).
6. Emit logs.

### 10.2 Candidate Selection Rules

A work item is dispatch-eligible only if:

- It has `id`, `identifier`, `title`, and `state`.
- Its state is in `active_states` and not in `terminal_states`.
- Required labels are present.
- It is not already `claimed` or `running`.
- A slot is available (v1: the single slot is free).
- Blocker rule: `Todo`-state items with non-terminal blockers are skipped.

Sorting: `priority` ascending → `created_at` oldest first → `identifier`
lexicographic.

### 10.3 Retry and Backoff

Identical to [Symphony §8.4]:

- Normal continuation: `1000 ms` fixed delay.
- Failure: `min(10000 * 2^(attempt - 1), max_retry_backoff_ms)`.

### 10.4 Reconciliation

Identical to [Symphony §8.5]:

- Part A: Stall detection using `stall_timeout_ms`.
- Part B: State refresh via adapter — terminal → stop + cleanup,
  active → update snapshot, other → stop without cleanup.

## 11. Agent Runner Protocol (Codex Integration)

### 11.1 Launch Contract

- Command: `codex.command` (default `codex app-server`).
- Invocation: `bash -lc <command>`.
- Working directory: the Harness-governed repository root.
- Transport: targeted Codex app-server protocol over stdio.

Note: v1 runs the agent in the repository root, NOT in a per-issue workspace
directory. The agent operates on the single repo clone.

### 11.2 Session Startup

Follows the targeted Codex app-server protocol [Symphony §10.2].

Symphony MUST:

- Initialize the session in the repo directory.
- Start the first turn with the rendered prompt.
- Start continuation turns with continuation guidance (not the full prompt).
- Extract `thread_id` and `turn_id` for session tracking.

### 11.3 Streaming Turn Processing

Identical to [Symphony §10.3]:

- Process events until turn terminates.
- Completion conditions: protocol success/failure/cancellation, turn timeout,
  subprocess exit.
- Continuation: start another turn on the same thread if still eligible.

### 11.4 Emitted Events

Key events forwarded to orchestrator:

- `session_started`, `turn_completed`, `turn_failed`, `turn_cancelled`
- `turn_input_required`, `notification`, `malformed`

### 11.5 Approval and Tool Policy

Implementation-defined [Symphony §10.5]. Each implementation MUST document its
posture. Runs MUST NOT stall indefinitely on approval or input requests.

### 11.6 Timeouts

- `codex.read_timeout_ms` — startup/sync timeout.
- `codex.turn_timeout_ms` — per-turn timeout.
- `codex.stall_timeout_ms` — enforced by orchestrator on event inactivity.

## 12. Observability

### 12.1 Logging

REQUIRED context fields for item-related logs:

- `item_id`, `item_identifier`, `source_kind`

REQUIRED context for session logs:

- `session_id`

### 12.2 Token Accounting

Identical to [Symphony §13.5]:

- Prefer absolute thread totals.
- Track deltas to avoid double-counting.
- Accumulate in orchestrator state.

### 12.3 TUI Dashboard (OPTIONAL, future)

When `--tui` flag is provided:

- Display active sessions, retry queue, aggregate totals.
- Keyboard controls for pause/resume/force-retry.
- Driven from orchestrator state only — MUST NOT affect correctness.

### 12.4 HTTP API (OPTIONAL, future)

When `--port <N>` is provided:

- `GET /api/v1/state` — runtime snapshot.
- `GET /api/v1/<identifier>` — item-specific debug details.
- `POST /api/v1/refresh` — trigger immediate poll.

## 13. Failure Model and Recovery

### 13.1 Failure Classes

1. `Workflow/Config` — Missing `WORKFLOW.md`, invalid YAML, missing source
   credentials.
2. `Agent Session` — Startup failure, turn failure/timeout/cancellation,
   stall, subprocess exit.
3. `Work Source` — API errors, auth failures, malformed payloads.
4. `Observability` — Log sink failure (non-fatal).

### 13.2 Recovery Behavior

- Config failures → skip dispatch, keep service alive.
- Agent failures → retry with exponential backoff.
- Source failures → skip this tick, retry next.
- Observability failures → do not crash orchestrator.

### 13.3 Restart Recovery

State is in-memory. After restart:

- No retry timers restored.
- No running sessions assumed recoverable.
- Recovery by: fresh polling + re-dispatch of eligible items.

## 14. Security and Safety

### 14.1 Trust Boundary

Implementation-defined [Symphony §15.1]. Each implementation MUST document
whether it targets trusted or restrictive environments.

### 14.2 Filesystem Safety

- Agent cwd MUST be the repository root.
- Repository path MUST be validated as a real directory before agent launch.

### 14.3 Secret Handling

- Support `$VAR` indirection in workflow config.
- Do not log API tokens or secret values.

### 14.4 Hook Safety

- Hooks are trusted config from `WORKFLOW.md`.
- Hooks run in the repo directory.
- Hook timeouts are REQUIRED.

## 15. Reference Algorithms

### 15.1 Service Startup

```text
function start_service():
  configure_logging()
  start_workflow_watch(on_change=reload_workflow)

  state = {
    poll_interval_ms: config.polling.interval_ms,
    running: {},
    claimed: set(),
    retry_attempts: {},
    completed: set(),
    codex_totals: {input: 0, output: 0, total: 0, seconds: 0}
  }

  validate_config() or fail_startup()
  schedule_tick(delay_ms=0)
  event_loop(state)
```

### 15.2 Poll-and-Dispatch Tick

```text
on_tick(state):
  state = reconcile(state)

  if validate_config() fails:
    log_error(); schedule_tick(); return state

  items = source_adapter.fetch_candidates()
  if items failed:
    log_error(); schedule_tick(); return state

  for item in sort_for_dispatch(items):
    if no_available_slots(state):
      break
    if should_dispatch(item, state):
      mode = route_intake(item, config)
      state = dispatch_item(item, state, attempt=null, mode=mode)

  schedule_tick(state.poll_interval_ms)
  return state
```

### 15.3 Dispatch One Item

```text
function dispatch_item(item, state, attempt, mode):
  worker = spawn_worker(
    fn -> run_agent(item, attempt, mode)
  )

  if spawn failed:
    return schedule_retry(state, item.id, ...)

  state.running[item.id] = {
    worker, identifier: item.identifier,
    item, mode, session_id: null,
    tokens: {0,0,0}, started_at: now()
  }
  state.claimed.add(item.id)
  return state
```

### 15.4 Worker Attempt

```text
function run_agent(item, attempt, mode):
  if run_hook("before_run") failed:
    fail_worker("before_run hook error")

  session = codex.start_session(cwd=repo_root)
  if session failed:
    run_hook_best_effort("after_run")
    fail_worker("session startup error")

  max_turns = config.agent.max_turns
  turn = 1

  while true:
    prompt = render_prompt(item, attempt, mode, turn, max_turns)
    result = codex.run_turn(session, prompt)

    if result failed:
      codex.stop(session)
      run_hook_best_effort("after_run")
      fail_worker("turn error")

    refreshed = source_adapter.fetch_states_by_ids([item.id])
    if refreshed.state is not active:
      break
    if turn >= max_turns:
      break
    turn += 1

  codex.stop(session)
  run_hook_best_effort("after_run")
  exit_normal()
```

### 15.5 Worker Exit Handling

```text
on_worker_exit(item_id, reason, state):
  entry = state.running.remove(item_id)
  state = add_runtime_to_totals(state, entry)

  if reason == normal:
    state.completed.add(item_id)
    state = schedule_retry(state, item_id, 1, continuation)
  else:
    state = schedule_retry(state, item_id, next_attempt(entry), error)

  return state
```

## 16. Implementation Checklist

### 16.1 REQUIRED for v1 Conformance

- [ ] `harness-core` crate with shared types, db access, config parsing
- [ ] `harness-symphony` crate as optional workspace member
- [ ] Workflow file loader with YAML front matter + prompt body
- [ ] Config layer with defaults and `$VAR` resolution
- [ ] Dynamic `WORKFLOW.md` watch/reload
- [ ] Work source adapter trait (`WorkSource`)
- [ ] Linear adapter (candidate fetch + state refresh + terminal fetch)
- [ ] Intake router (inline vs dedicated mode dispatch)
- [ ] Polling orchestrator with single-authority state
- [ ] Single-slot dispatch (one agent at a time)
- [ ] Codex app-server subprocess client
- [ ] Strict prompt rendering with `item`, `attempt`, `mode` variables
- [ ] Retry queue with exponential backoff + continuation retries
- [ ] Reconciliation (stall detection + state refresh)
- [ ] Structured logs with `item_id`, `item_identifier`, `session_id`
- [ ] `before_run` and `after_run` hooks with timeout
- [ ] `install-harness.sh --with-symphony` flag

### 16.2 RECOMMENDED Extensions (v2+)

- [ ] Multi-agent concurrency with shared-state strategy
- [ ] TUI dashboard (`--tui`)
- [ ] HTTP API (`--port`)
- [ ] GitHub Issues adapter
- [ ] Harness backlog adapter (read stories/backlog from `harness.db`)
- [ ] SSH worker extension for remote execution
- [ ] Persistent retry queue across restarts

### 16.3 Operational Validation

- [ ] Run with valid Linear credentials end-to-end
- [ ] Verify hook execution on target OS
- [ ] Verify `WORKFLOW.md` reload applies without restart

## 17. Interaction with Harness Lifecycle

This section documents how the Harness protocol plays out inside a
Symphony-launched agent session, for implementor reference. Symphony does NOT
enforce any of these steps — the agent follows them autonomously.

### 17.1 Inline Mode Session

```text
Agent starts in repo with rendered prompt containing work item.
  1. Agent reads AGENTS.md → directed to Harness docs.
  2. Agent reads FEATURE_INTAKE.md → classifies input type + risk lane.
  3. Agent records: harness-cli intake --type X --summary "..." --lane Y.
  4. Agent reads CONTEXT_RULES.md → loads docs per phase + lane.
  5. Agent does the work (code, tests, docs).
  6. Agent records: harness-cli trace --summary "..." --outcome completed.
  7. Agent runs: harness-cli story verify <id> (if applicable).
  8. Agent records friction: harness-cli backlog add (if encountered).
  9. Agent exits.
```

### 17.2 Dedicated Intake Mode Session

```text
Agent starts in repo with intake-mode prompt.
  1. Agent reads AGENTS.md → directed to Harness docs.
  2. Agent reads FEATURE_INTAKE.md → classifies input type.
  3. Agent generates work artifacts:
     - For new_spec: product docs, candidate epics, architecture questions.
     - For new_initiative: initiative notes, candidate story packets.
  4. Agent writes artifacts to docs/stories/, docs/product/, etc.
  5. Agent records: harness-cli intake --type new_spec --summary "...".
  6. Agent records: harness-cli story add (for each generated story).
  7. Agent exits. Generated stories are now in the repo and harness.db.
```

The scheduler picks up generated stories on the next cycle (if using a
Harness backlog adapter) or the operator creates tracker tickets for them.

### 17.3 Cross-Run Intelligence

After N agent runs, accumulated data in `harness.db` supports:

- `harness-cli audit` → entropy/drift score.
- `harness-cli propose` → improvement proposals from friction patterns.
- `harness-cli query friction` → repeated pain points.
- `harness-cli query traces` → execution patterns.

These can be run manually, via cron, or by a future intelligence service
extension. Symphony does not run them automatically in v1.

## Appendix A. Example WORKFLOW.md

```yaml
---
source:
  kind: linear
  api_key: $LINEAR_API_KEY
  project_slug: harness-demo
  active_states: ["Todo", "In Progress"]
  terminal_states: ["Done", "Cancelled"]

polling:
  interval_ms: 30000

agent:
  max_turns: 20
  max_retry_backoff_ms: 300000

codex:
  command: codex app-server
  approval_policy: auto-edit
  turn_timeout_ms: 3600000
  stall_timeout_ms: 300000

hooks:
  before_run: |
    git fetch origin
    git checkout -B work/$ITEM_IDENTIFIER origin/main
  after_run: |
    harness-cli audit || true

intake:
  dedicated_types: ["new_spec", "new_initiative"]
  default_mode: inline
---
You are working on {{ item.identifier }}: {{ item.title }}.

Follow AGENTS.md in this repository. It will direct you to the Harness
operating docs for intake classification, context loading, and trace recording.

{% if mode == "intake" %}
## Intake Mode

This is a DEDICATED INTAKE session. Your job is to:
1. Read docs/FEATURE_INTAKE.md and classify this input.
2. Generate the appropriate work artifacts (stories, epics, product docs).
3. Record the intake via harness-cli intake.
4. Do NOT implement code — only decompose and plan.
{% endif %}

{% if item.description %}
## Work Item

{{ item.description }}
{% endif %}

{% if attempt %}
This is continuation attempt {{ attempt }}. Review previous work and continue
from where you left off.
{% endif %}
```

## Appendix B. Glossary Additions

- **Work Source** — Pluggable adapter that fetches dispatchable work items
  (Linear issues, GitHub issues, Harness stories/backlog items).
- **Intake Router** — Component that decides whether a work item needs a
  dedicated intake session or can be dispatched directly for inline intake.
- **Inline Intake** — The agent handles intake classification as its first
  step within the same session that does the work.
- **Dedicated Intake** — A separate agent session that only does intake
  (classify, decompose, generate stories) without implementing.
- **Harness Protocol** — The set of behaviors an agent follows by reading
  Harness docs (AGENTS.md, FEATURE_INTAKE.md, CONTEXT_RULES.md, etc.).
  Not enforced by the orchestrator.

## Appendix C. Migration from v1 Spec

The previous draft (v1) made several assumptions corrected by the audit:

| v1 Assumption | v2 Correction |
|---|---|
| Orchestrator classifies intake | Agent classifies intake autonomously |
| Per-story workspaces with own harness.db | Single repo clone, shared harness.db |
| Orchestrator assembles context per lane | Agent follows CONTEXT_RULES.md |
| Orchestrator runs verification gates | Agent runs harness-cli story verify |
| Lane → Codex approval policy mapping | Orthogonal concerns, not coupled |
| Orchestrator state in harness.db | In-memory state (scheduler ≠ ops memory) |
| Full Symphony complexity (100+ agents) | Single agent v1, concurrency deferred |
| Linear-only work source | Pluggable adapter interface |

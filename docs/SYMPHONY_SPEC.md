# Harness Symphony Service Specification

Status: Draft v1 (language-agnostic)

Purpose: Define a service that orchestrates coding agents within the Harness
operating model — combining Symphony's daemon scheduling with Harness's
structured context, risk classification, durable state, and verification gates.

## Normative Language

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`,
`RECOMMENDED`, `MAY`, and `OPTIONAL` in this document are to be interpreted as
described in RFC 2119.

`Implementation-defined` means the behavior is part of the implementation
contract, but this specification does not prescribe one universal policy.
Implementations MUST document the selected behavior.

## 1. Problem Statement

Harness Symphony is a long-running automation service that continuously reads
work from an issue tracker or a Harness-managed story backlog, classifies each
item through the Harness feature intake gate, creates an isolated workspace
with the Harness context layer installed, and runs a coding agent session
inside that workspace under Harness operating rules.

The service solves six operational problems:

- It turns story execution into a repeatable daemon workflow instead of manual
  agent sessions.
- It isolates agent execution in per-story workspaces where agents operate
  under Harness context rules (`docs/CONTEXT_RULES.md`).
- It classifies every work item through the Harness feature intake gate
  (`docs/FEATURE_INTAKE.md`) before dispatching, so risk lanes govern agent
  behavior, approval policy, and verification depth.
- It keeps the workflow policy in-repo (`WORKFLOW.md` + Harness docs) so teams
  version both the agent prompt and the operating harness with their code.
- It records durable execution traces through the Harness CLI so every agent
  run produces structured, queryable evidence in `harness.db`.
- It feeds friction and failures back into the Harness improvement loop so the
  operating environment evolves after every batch of work.

Important boundaries:

- Harness Symphony is a scheduler/runner, tracker reader, and Harness-aware
  lifecycle manager.
- Ticket writes (state transitions, comments, PR links) are typically performed
  by the coding agent using tools available in the workflow environment.
- A successful run can end at a workflow-defined handoff state (for example
  `Human Review`), not necessarily `Done`.
- The Harness context layer (docs, templates, durable state, CLI) is the
  agent's operating environment. Symphony does not replace Harness — it
  orchestrates work within it.

## 2. Goals and Non-Goals

### 2.1 Goals

- Poll the issue tracker on a fixed cadence and dispatch work with bounded
  concurrency.
- Classify every dispatched item through the Harness intake gate before agent
  execution begins.
- Set agent approval policy, verification depth, and context requirements based
  on the classified risk lane (tiny, normal, high-risk).
- Maintain a single authoritative orchestrator state for dispatch, retries, and
  reconciliation, backed by the Harness durable layer (SQLite).
- Create deterministic per-story workspaces with the Harness context layer
  installed and `harness.db` initialized.
- Record structured execution traces through `harness-cli trace` at the end of
  every agent run, scored against `docs/TRACE_SPEC.md` tier requirements.
- Run story verification gates (`harness-cli story verify`) before marking work
  complete.
- Stop active runs when issue state changes make them ineligible.
- Recover from transient failures with exponential backoff.
- Load runtime behavior from a repository-owned `WORKFLOW.md` contract that
  extends the Harness operating docs.
- Expose operator-visible observability (structured logs, durable traces,
  entropy audits).
- Feed harness friction into the improvement pipeline
  (`harness-cli backlog add`, `harness-cli propose`).

### 2.2 Non-Goals

- Rich web UI or multi-tenant control plane.
- General-purpose workflow engine or distributed job scheduler.
- Built-in business logic for how to edit tickets, PRs, or comments (that logic
  lives in the workflow prompt and agent tooling).
- Replacing the Harness CLI or durable layer — Symphony consumes and writes to
  it, never bypasses it.
- Mandating a single sandbox or approval posture for all implementations.

## 3. System Overview

### 3.1 Main Components

1. `Workflow Loader`
   - Reads `WORKFLOW.md`.
   - Parses YAML front matter and prompt body.
   - Resolves Harness-specific extensions (intake policy, lane overrides,
     verification requirements).
   - Returns `{config, prompt_template}`.

2. `Config Layer`
   - Exposes typed getters for workflow config values.
   - Applies defaults and environment variable indirection.
   - Validates Harness-specific fields (lane policies, trace requirements,
     context rules).

3. `Issue Tracker Client`
   - Fetches candidate issues in active states.
   - Fetches current states for specific issue IDs (reconciliation).
   - Normalizes tracker payloads into a stable issue model enriched with
     Harness metadata (linked stories, intake IDs, lane hints from labels).
   - Supports multiple tracker backends: Linear (default), GitHub Issues,
     or Harness story backlog as a local source.

4. `Intake Classifier`
   - NEW component unique to Harness Symphony.
   - Runs the `docs/FEATURE_INTAKE.md` risk checklist against each candidate
     issue before dispatch.
   - Records the classification via `harness-cli intake`.
   - Returns the risk lane (`tiny`, `normal`, `high-risk`) and the set of
     triggered risk flags.
   - The lane governs agent prompt construction, approval policy, context
     loading, and verification depth.

5. `Orchestrator`
   - Owns the poll tick.
   - Owns the runtime state (backed by SQLite for persistence across restarts).
   - Decides which issues to dispatch, retry, stop, or release.
   - Tracks session metrics, retry queue state, and Harness-specific counters
     (intake counts, trace scores, friction items).

6. `Workspace Manager`
   - Maps issue identifiers to workspace paths.
   - Ensures per-story workspace directories exist with the Harness context
     layer installed (`harness-cli init`, Harness docs copied or symlinked).
   - Runs workspace lifecycle hooks.
   - Cleans workspaces for terminal issues.

7. `Agent Runner`
   - Creates workspace with Harness context.
   - Builds prompt from issue + workflow template + Harness context (lane,
     story packet, relevant product docs, architecture rules).
   - Launches the coding agent.
   - Streams agent updates back to the orchestrator.
   - On completion, records a structured trace via `harness-cli trace`.

8. `Verification Gate`
   - NEW component unique to Harness Symphony.
   - After agent completion, runs `harness-cli story verify <id>` for linked
     stories.
   - Runs `harness-cli story verify-all` for high-risk work.
   - Evaluates trace quality via `harness-cli score-trace`.
   - Reports verification status back to the orchestrator to decide if work
     meets the lane's proof requirements.

9. `Friction Collector`
   - NEW component unique to Harness Symphony.
   - Extracts `harness_friction` from agent traces.
   - Records friction items via `harness-cli backlog add` when patterns repeat.
   - Periodically runs `harness-cli propose` to generate improvement proposals
     from accumulated friction.

10. `Status Surface` (OPTIONAL)
    - Presents human-readable runtime status enriched with Harness metrics
      (trace scores, lane distribution, verification pass rates, entropy score).

11. `Logging`
    - Emits structured runtime logs to one or more configured sinks.
    - Includes Harness context fields (lane, story_id, intake_id, trace_score).

### 3.2 Abstraction Levels

Harness Symphony is easiest to port when kept in these layers:

1. `Policy Layer` (repo-defined)
   - `WORKFLOW.md` prompt body.
   - Harness operating docs (`AGENTS.md`, `docs/FEATURE_INTAKE.md`,
     `docs/CONTEXT_RULES.md`, `docs/HARNESS.md`).
   - Team-specific rules for ticket handling, validation, and handoff.

2. `Harness Layer` (context + durable state)
   - Feature intake classification.
   - Risk lane governance.
   - Context engineering rules.
   - Trace recording and scoring.
   - Story verification gates.
   - Friction capture and improvement pipeline.

3. `Configuration Layer` (typed getters)
   - Parses front matter into typed runtime settings.
   - Handles defaults, environment tokens, and path normalization.
   - Merges Harness-specific config with Symphony core config.

4. `Coordination Layer` (orchestrator)
   - Polling loop, issue eligibility, concurrency, retries, reconciliation.
   - Lane-aware dispatch priorities and concurrency limits.

5. `Execution Layer` (workspace + agent subprocess)
   - Filesystem lifecycle, Harness context installation, workspace preparation,
     coding-agent protocol.

6. `Integration Layer` (tracker adapter)
   - API calls and normalization for tracker data.
   - Harness story backlog as an additional (or primary) work source.

7. `Observability Layer` (logs + traces + status surface)
   - Operator visibility into orchestrator and agent behavior.
   - Durable trace records with quality scoring.
   - Entropy auditing and improvement proposals.

### 3.3 External Dependencies

- Issue tracker API (Linear, GitHub Issues, or Harness story backlog).
- Local filesystem for workspaces and logs.
- SQLite (`harness.db`) for durable operational state.
- Harness CLI binary (`scripts/bin/harness-cli`) for durable operations.
- Harness docs hierarchy (installed or symlinked into each workspace).
- Coding-agent executable (Codex app-server, Claude Code, Cursor, Devin, or
  compatible agent).
- Host environment authentication for the issue tracker and coding agent.

## 4. Core Domain Model

### 4.1 Entities

#### 4.1.1 Issue (Extended)

Normalized issue record enriched with Harness metadata.

Fields (inherited from Symphony):

- `id` (string) — Stable tracker-internal ID.
- `identifier` (string) — Human-readable ticket key.
- `title` (string)
- `description` (string or null)
- `priority` (integer or null)
- `state` (string)
- `branch_name` (string or null)
- `url` (string or null)
- `labels` (list of strings, normalized to lowercase)
- `blocked_by` (list of blocker refs)
- `created_at` (timestamp or null)
- `updated_at` (timestamp or null)

Fields (Harness extensions):

- `intake_id` (integer or null) — ID from the Harness `intake` table once
  classified.
- `lane` (string or null) — Risk lane assigned during intake: `tiny`,
  `normal`, or `high-risk`.
- `risk_flags` (list of strings) — Risk checklist flags triggered during
  intake (e.g., `Auth`, `Data model`, `Public contracts`).
- `story_id` (string or null) — Linked Harness story ID when the issue maps
  to a tracked story (e.g., `US-014`).
- `input_type` (string or null) — Harness input type from intake
  classification (e.g., `spec_slice`, `change_request`, `maintenance`).

#### 4.1.2 Workflow Definition

Parsed `WORKFLOW.md` payload:

- `config` (map) — YAML front matter root object.
- `prompt_template` (string) — Markdown body after front matter, trimmed.

#### 4.1.3 Service Config (Typed View)

Typed runtime values derived from `WorkflowDefinition.config` plus environment
resolution.

Core fields (inherited from Symphony):

- poll interval
- workspace root
- active and terminal issue states
- concurrency limits
- coding-agent executable/args/timeouts
- workspace hooks

Harness-specific fields:

- `harness.auto_intake` (boolean, default `true`) — Run intake classification
  automatically before dispatch.
- `harness.trace_tier` (string, default `lane`) — Minimum trace quality tier.
  `lane` means the tier follows the classified lane (tiny→minimal,
  normal→standard, high-risk→detailed). Can also be `minimal`, `standard`, or
  `detailed` to override.
- `harness.verify_before_complete` (boolean, default `true`) — Run story
  verification gates before marking work complete.
- `harness.context_scoring` (boolean, default `true`) — Score context
  selection against `docs/CONTEXT_RULES.md` after each trace.
- `harness.friction_threshold` (integer, default `3`) — Number of repeated
  friction patterns before auto-creating a backlog item.
- `harness.propose_interval` (integer, default `10`) — Run
  `harness-cli propose` every N completed traces.
- `harness.lane_concurrency` (map, OPTIONAL) — Per-lane concurrency limits.
  Example: `{"high-risk": 1, "normal": 5, "tiny": 10}`.
- `harness.lane_approval` (map, OPTIONAL) — Per-lane approval policies.
  Example: `{"high-risk": "human_confirm", "normal": "auto_approve",
  "tiny": "auto_approve"}`.

#### 4.1.4 Workspace (Extended)

Filesystem workspace assigned to one issue/story with Harness installed.

Fields (logical):

- `path` (absolute workspace path)
- `workspace_key` (sanitized issue identifier)
- `created_now` (boolean)
- `harness_initialized` (boolean) — Whether `harness-cli init` has been run.
- `harness_db_path` (absolute path to `harness.db` within workspace)

#### 4.1.5 Run Attempt (Extended)

One execution attempt for one issue, with Harness metadata.

Fields (logical):

- `issue_id`
- `issue_identifier`
- `attempt` (integer or null)
- `workspace_path`
- `started_at`
- `status`
- `error` (OPTIONAL)
- `lane` (string) — Risk lane for this attempt.
- `intake_id` (integer or null) — Linked intake record.
- `story_id` (string or null) — Linked story record.
- `trace_id` (integer or null) — ID of the trace recorded after completion.
- `trace_score` (integer or null) — Quality score from `score-trace`.
- `verification_passed` (boolean or null) — Story verification result.

#### 4.1.6 Live Session (Agent Session Metadata)

State tracked while a coding-agent subprocess is running.

Fields (inherited from Symphony):

- `session_id` (string)
- `thread_id` (string)
- `turn_id` (string)
- `agent_pid` (string or null)
- `last_agent_event` (string or null)
- `last_agent_timestamp` (timestamp or null)
- `last_agent_message` (summarized payload)
- `input_tokens` (integer)
- `output_tokens` (integer)
- `total_tokens` (integer)
- `turn_count` (integer)

Fields (Harness extensions):

- `lane` (string) — Active risk lane.
- `context_docs_loaded` (list of strings) — Harness docs loaded by the agent
  during this session (for context scoring).
- `friction_items` (list of strings) — Friction discovered during execution.

#### 4.1.7 Retry Entry

Scheduled retry state for an issue.

Fields:

- `issue_id`
- `identifier`
- `attempt` (integer, 1-based)
- `due_at_ms` (monotonic clock timestamp)
- `timer_handle` (runtime-specific)
- `error` (string or null)
- `lane` (string) — Preserved lane from the failed attempt.

#### 4.1.8 Orchestrator Runtime State

Single authoritative state owned by the orchestrator.

Fields (inherited from Symphony):

- `poll_interval_ms`
- `max_concurrent_agents`
- `running` (map `issue_id -> running entry`)
- `claimed` (set of issue IDs)
- `retry_attempts` (map `issue_id -> RetryEntry`)
- `completed` (set of issue IDs)
- `agent_totals` (aggregate tokens + runtime seconds)
- `rate_limits` (latest rate-limit snapshot)

Fields (Harness extensions):

- `lane_counts` (map `lane -> running count`) — Per-lane concurrency tracking.
- `trace_scores` (running average of trace quality scores)
- `friction_accumulator` (map `friction_pattern -> count`) — Tracks repeated
  friction for auto-backlog creation.
- `last_propose_trace_count` (integer) — Trace count at last proposal
  generation.
- `entropy_score` (float or null) — Latest score from `harness-cli audit`.

### 4.2 Stable Identifiers and Normalization Rules

- `Issue ID` — Use for tracker lookups and internal map keys.
- `Issue Identifier` — Use for human-readable logs and workspace naming.
- `Workspace Key` — Derive from `issue.identifier` by replacing any character
  not in `[A-Za-z0-9._-]` with `_`.
- `Story ID` — Use the Harness story ID (e.g., `US-014`) when the issue maps
  to a tracked story.
- `Lane` — Always one of `tiny`, `normal`, or `high-risk`. Normalize before
  comparison.
- `Session ID` — Compose from agent `thread_id` and `turn_id`.

## 5. Workflow Specification (Repository Contract)

### 5.1 File Discovery and Path Resolution

Workflow file path precedence:

1. Explicit application/runtime setting (set by CLI startup path).
2. Default: `WORKFLOW.md` in the current process working directory.

Loader behavior:

- If the file cannot be read, return `missing_workflow_file` error.
- The workflow file is expected to be repository-owned and version-controlled.

### 5.2 File Format

`WORKFLOW.md` is a Markdown file with OPTIONAL YAML front matter.

Parsing rules:

- If file starts with `---`, parse lines until the next `---` as YAML.
- Remaining lines become the prompt body.
- If front matter is absent, treat the entire file as prompt body and use an
  empty config map.
- YAML front matter MUST decode to a map/object.
- Prompt body is trimmed before use.

### 5.3 Front Matter Schema

Top-level keys:

- `tracker`
- `polling`
- `workspace`
- `hooks`
- `agent`
- `codex` (or `runner` — agent-neutral alias)
- `harness` (NEW — Harness-specific configuration)

Unknown keys SHOULD be ignored for forward compatibility.

#### 5.3.1 `tracker` (object)

Fields:

- `kind` (string) — REQUIRED for dispatch.
  Supported values: `linear`, `github`, `harness_backlog`.
- `endpoint` (string) — Default depends on `tracker.kind`.
- `api_key` (string) — MAY be a literal token or `$VAR_NAME`.
- `project_slug` (string) — REQUIRED for `linear` and `github`.
- `required_labels` (list of strings, default `[]`)
- `active_states` (list of strings) — Defaults depend on `tracker.kind`.
- `terminal_states` (list of strings) — Defaults depend on `tracker.kind`.

When `tracker.kind == "harness_backlog"`:

- The orchestrator reads from the local `harness.db` story table instead of an
  external tracker.
- Stories with `status = 'planned'` or `status = 'in_progress'` are candidates.
- Stories with `status = 'implemented'` or `status = 'retired'` are terminal.
- `tracker.api_key` and `tracker.project_slug` are not required.

#### 5.3.2 `polling` (object)

Fields:

- `interval_ms` (integer, default `30000`)

#### 5.3.3 `workspace` (object)

Fields:

- `root` (path string or `$VAR`, default `<system-temp>/harness_workspaces`)
- `harness_source` (path string, OPTIONAL) — Path to a Harness repository to
  install from. When set, new workspaces are bootstrapped with
  `install-harness.sh --merge --yes` from this source.

#### 5.3.4 `hooks` (object)

Fields:

- `after_create` (shell script, OPTIONAL) — Runs after workspace creation.
  Default Harness behavior: run `harness-cli init` if `harness.db` does not
  exist.
- `before_run` (shell script, OPTIONAL) — Runs before each agent attempt.
  Default Harness behavior: run `harness-cli intake` with auto-classification
  when `harness.auto_intake` is true.
- `after_run` (shell script, OPTIONAL) — Runs after each agent attempt.
  Default Harness behavior: record trace via `harness-cli trace`, run
  verification gates, score context.
- `before_remove` (shell script, OPTIONAL)
- `timeout_ms` (integer, default `60000`)

#### 5.3.5 `agent` (object)

Fields:

- `max_concurrent_agents` (integer, default `10`)
- `max_turns` (positive integer, default `20`)
- `max_retry_backoff_ms` (integer, default `300000`)
- `max_concurrent_agents_by_state` (map, default `{}`)
- `kind` (string, OPTIONAL) — Agent runtime type. Supported values:
  `codex`, `claude_code`, `cursor`, `devin`, `generic`. When set, the runner
  adapts its launch protocol to the specified agent. Default:
  implementation-defined.

#### 5.3.6 `harness` (object) — NEW

Fields:

- `auto_intake` (boolean, default `true`)
- `trace_tier` (string, default `lane`)
- `verify_before_complete` (boolean, default `true`)
- `context_scoring` (boolean, default `true`)
- `friction_threshold` (integer, default `3`)
- `propose_interval` (integer, default `10`)
- `lane_concurrency` (map, OPTIONAL)
- `lane_approval` (map, OPTIONAL)
- `audit_interval` (integer, default `50`) — Run `harness-cli audit` every N
  completed traces to measure drift.
- `maturity_target` (string, OPTIONAL) — Target maturity level (e.g., `H3`).
  When set, the orchestrator logs warnings when operational metrics fall below
  the target level's benchmark indicators.

### 5.4 Prompt Template Contract

The Markdown body of `WORKFLOW.md` is the per-issue prompt template.

Template input variables:

- `issue` (object) — All normalized issue fields including Harness extensions.
- `attempt` (integer or null) — Retry/continuation metadata.
- `lane` (string) — Classified risk lane.
- `risk_flags` (list of strings) — Triggered risk flags.
- `story` (object or null) — Linked story record with proof status.
- `harness_context` (string) — Pre-assembled Harness context document
  containing the documents required for the classified lane and current
  context phase per `docs/CONTEXT_RULES.md`.
- `verification_status` (object or null) — Current proof matrix row for the
  linked story.

### 5.5 Workflow Validation and Error Surface

Error classes:

- `missing_workflow_file`
- `workflow_parse_error`
- `workflow_front_matter_not_a_map`
- `template_parse_error`
- `template_render_error`
- `harness_config_invalid` — Invalid `harness.*` configuration.
- `intake_classification_failed` — Intake classifier could not determine lane.

## 6. Configuration Specification

### 6.1 Configuration Resolution Pipeline

1. Select the workflow file path.
2. Parse YAML front matter.
3. Apply built-in defaults for missing OPTIONAL fields.
4. Resolve `$VAR_NAME` indirection.
5. Coerce and validate typed values.
6. Merge Harness-specific config with defaults from `docs/HARNESS.md`.

### 6.2 Dynamic Reload Semantics

- The software MUST detect `WORKFLOW.md` changes.
- On change, it MUST re-read and re-apply workflow config and prompt template
  without restart.
- The software SHOULD also watch Harness operating docs for changes (a
  `docs/FEATURE_INTAKE.md` update should affect future intake classifications).
- Invalid reloads MUST NOT crash the service.

### 6.3 Dispatch Preflight Validation

Startup validation:

- Validate configuration before starting the scheduling loop.
- Validate Harness CLI is available and `harness.db` can be initialized.

Per-tick dispatch validation:

- Re-validate before each dispatch cycle.
- Verify `harness-cli` binary is accessible.
- If validation fails, skip dispatch for that tick.

### 6.4 Core Config Fields Summary

Symphony core fields (see Symphony SPEC.md §6.4 for full list):

- `tracker.kind`, `tracker.endpoint`, `tracker.api_key`,
  `tracker.project_slug`, `tracker.required_labels`,
  `tracker.active_states`, `tracker.terminal_states`
- `polling.interval_ms`
- `workspace.root`
- `hooks.after_create`, `hooks.before_run`, `hooks.after_run`,
  `hooks.before_remove`, `hooks.timeout_ms`
- `agent.max_concurrent_agents`, `agent.max_turns`,
  `agent.max_retry_backoff_ms`, `agent.max_concurrent_agents_by_state`

Harness-specific fields (new):

- `harness.auto_intake`, `harness.trace_tier`,
  `harness.verify_before_complete`, `harness.context_scoring`,
  `harness.friction_threshold`, `harness.propose_interval`,
  `harness.lane_concurrency`, `harness.lane_approval`,
  `harness.audit_interval`, `harness.maturity_target`

## 7. Orchestration State Machine

### 7.1 Issue Orchestration States

1. `Unclaimed` — Not running, no retry scheduled.
2. `Classifying` — NEW. Intake classification in progress.
3. `Claimed` — Reserved for dispatch (running or retrying).
4. `Running` — Worker task exists.
5. `Verifying` — NEW. Post-completion verification gates running.
6. `RetryQueued` — Retry timer exists.
7. `Released` — Claim removed (terminal, non-active, or retry exhausted).

### 7.2 Run Attempt Lifecycle

1. `ClassifyingIntake` — NEW. Running intake risk checklist.
2. `PreparingWorkspace`
3. `InstallingHarnessContext` — NEW. Ensuring Harness docs and CLI are
   available in workspace.
4. `BuildingPrompt`
5. `LaunchingAgentProcess`
6. `InitializingSession`
7. `StreamingTurn`
8. `RecordingTrace` — NEW. Writing trace via `harness-cli trace`.
9. `RunningVerification` — NEW. Running story verification gates.
10. `ScoringContext` — NEW. Running `harness-cli score-context`.
11. `Finishing`
12. `Succeeded`
13. `SucceededWithWarnings` — NEW. Completed but verification or trace quality
    did not meet lane requirements.
14. `Failed`
15. `TimedOut`
16. `Stalled`
17. `CanceledByReconciliation`

### 7.3 Transition Triggers

Inherited from Symphony:

- `Poll Tick` — Reconcile, validate, fetch, dispatch.
- `Worker Exit (normal)` — Record trace, run verification, schedule
  continuation.
- `Worker Exit (abnormal)` — Record trace with `outcome: failed`, schedule
  retry.
- `Agent Update Event` — Update live session fields.
- `Retry Timer Fired` — Re-dispatch or release.
- `Reconciliation State Refresh` — Stop ineligible runs.
- `Stall Timeout` — Kill worker, schedule retry.

Harness-specific triggers:

- `Intake Classification Complete` — Lane assigned, dispatch proceeds with
  lane-appropriate prompt and approval policy.
- `Verification Gate Complete` — Verification passed or failed. Failed
  verification on high-risk work blocks auto-completion.
- `Friction Threshold Reached` — Auto-create backlog item.
- `Proposal Interval Reached` — Run `harness-cli propose`.
- `Audit Interval Reached` — Run `harness-cli audit` and record entropy score.

### 7.4 Idempotency and Recovery Rules

Inherited from Symphony:

- Single-authority state mutations.
- `claimed` and `running` checks before launching any worker.
- Reconciliation runs before dispatch on every tick.

Harness-specific recovery:

- On restart, the orchestrator recovers state from `harness.db` in addition to
  polling the tracker. Story status, intake records, and recent traces provide
  richer recovery context than tracker state alone.
- Incomplete traces (agent started but no trace recorded) are detected during
  startup and recorded as `outcome: failed` with a note indicating unclean
  shutdown.

## 8. Polling, Scheduling, and Reconciliation

### 8.1 Poll Loop

At startup:

1. Validate config.
2. Verify Harness CLI and database.
3. Perform startup terminal cleanup.
4. Schedule immediate tick.
5. Repeat every `polling.interval_ms`.

Tick sequence:

1. Reconcile running issues.
2. Run dispatch preflight validation.
3. Fetch candidate issues from tracker.
4. Classify candidates through intake gate (if `harness.auto_intake`).
5. Sort issues by dispatch priority (lane-aware).
6. Dispatch eligible issues while slots remain.
7. Check friction and proposal thresholds.
8. Notify observability consumers.

### 8.2 Candidate Selection Rules (Extended)

An issue is dispatch-eligible only if all are true:

- Standard Symphony eligibility checks (§8.2 of Symphony SPEC).
- Intake classification succeeded (lane is assigned).
- Lane-specific concurrency slots are available (when
  `harness.lane_concurrency` is configured).
- For `high-risk` lane: no other `high-risk` item is running unless explicitly
  allowed by `harness.lane_concurrency`.

Sorting order (extended):

1. Lane priority: `high-risk` first (to avoid starving complex work), then
   `normal`, then `tiny`.
2. `priority` ascending (1..4 preferred; null sorts last).
3. `created_at` oldest first.
4. `identifier` lexicographic tie-breaker.

### 8.3 Concurrency Control (Extended)

Global limit: inherited from Symphony.

Per-lane limit (new):

- `harness.lane_concurrency[lane]` if present.
- Otherwise fallback to global limit.

Per-state limit: inherited from Symphony.

### 8.4 Retry and Backoff

Inherited from Symphony with one Harness extension:

- High-risk failures use longer initial retry delay: `20000 * 2^(attempt - 1)`
  instead of `10000 * 2^(attempt - 1)`.
- Tiny-lane failures use shorter max backoff: `60000` (1 minute) instead of
  `300000` (5 minutes).

### 8.5 Active Run Reconciliation

Inherited from Symphony (stall detection + tracker state refresh).

### 8.6 Startup Recovery (Extended)

When the service starts:

1. Standard Symphony startup terminal cleanup.
2. Query `harness.db` for stories with `status = 'in_progress'` and no recent
   trace. Log these as potential orphaned runs.
3. Run `harness-cli audit` to establish baseline entropy score.

## 9. Workspace Management and Safety

### 9.1 Workspace Layout

```text
<workspace.root>/
  <sanitized_identifier>/
    AGENTS.md
    docs/
      HARNESS.md
      FEATURE_INTAKE.md
      CONTEXT_RULES.md
      ARCHITECTURE.md
      TEST_MATRIX.md
      TRACE_SPEC.md
      ...
    scripts/
      bin/
        harness-cli
    harness.db
    WORKFLOW.md (symlinked or copied from source repo)
    <project source files>
```

### 9.2 Workspace Creation (Extended)

1. Sanitize identifier to `workspace_key`.
2. Compute workspace path.
3. Create directory if needed.
4. If new workspace:
   a. Install Harness context (from `workspace.harness_source` or embedded).
   b. Run `harness-cli init` to create `harness.db`.
   c. Run `after_create` hook.
5. If existing workspace:
   a. Verify `harness.db` exists; reinitialize if missing.
   b. Run `harness-cli migrate` to apply any schema updates.

### 9.3 Safety Invariants

Inherited from Symphony:

- Agent cwd MUST be the per-issue workspace path.
- Workspace path MUST stay inside workspace root.
- Workspace directory names MUST use sanitized identifiers.

## 10. Agent Runner Protocol

### 10.1 Launch Contract

The agent runner is agent-neutral. When `agent.kind` is set:

- `codex`: Launch via `bash -lc <codex.command>` with Codex app-server
  protocol.
- `claude_code`: Launch Claude Code with `--print` mode or MCP protocol.
- `cursor`: Launch via Cursor CLI with workspace path.
- `devin`: Launch via Devin API with session parameters.
- `generic`: Launch a shell command and communicate via stdin/stdout.

All agents receive:

- Workspace path as working directory.
- Rendered prompt with Harness context.
- Lane-appropriate approval policy.

### 10.2 Session Startup (Extended)

In addition to standard Symphony session startup:

- Supply Harness context documents to the agent prompt based on the classified
  lane and current context phase (`docs/CONTEXT_RULES.md`).
- For `normal` and `high-risk` lanes, include the linked story packet in the
  prompt context.
- For `high-risk` lanes, include relevant decision records and architecture
  docs.
- Set approval policy based on `harness.lane_approval[lane]`.

### 10.3 Streaming Turn Processing

Inherited from Symphony.

During streaming, the runner SHOULD extract:

- File read events (for context scoring).
- Friction indicators (agent confusion, repeated failures, missing context).
- Decision-making moments (for trace `decisions_made` field).

### 10.4 Post-Run Harness Operations

After each agent run (before `after_run` hook):

1. **Record Trace**: Build trace fields from the agent session and record via
   `harness-cli trace --summary <summary> --outcome <outcome> --story <id>
   --intake <id> --agent <kind> --actions-taken <actions> --files-read <files>
   --files-changed <files> --harness-friction <friction>`.

2. **Score Trace**: Run `harness-cli score-trace --id <trace_id>`. Compare
   score against lane requirements (`docs/TRACE_SPEC.md`).

3. **Score Context**: If `harness.context_scoring` is true, run
   `harness-cli score-context <trace_id>`.

4. **Verify Stories**: If `harness.verify_before_complete` is true and a story
   is linked, run `harness-cli story verify <story_id>`.

5. **Collect Friction**: Extract `harness_friction` from the trace. Increment
   friction accumulator. If threshold reached, run
   `harness-cli backlog add --title <pattern> --pain <friction>`.

6. **Check Proposal Interval**: If completed trace count mod
   `harness.propose_interval == 0`, run `harness-cli propose`.

7. **Check Audit Interval**: If completed trace count mod
   `harness.audit_interval == 0`, run `harness-cli audit`.

## 11. Issue Tracker Integration

### 11.1 Supported Trackers

- `linear` — Full Symphony Linear integration (see Symphony SPEC §11).
- `github` — GitHub Issues/Projects integration.
- `harness_backlog` — Local Harness story backlog as work source.

### 11.2 Harness Backlog Tracker

When `tracker.kind == "harness_backlog"`:

- Candidate issues are read from `SELECT * FROM story WHERE status IN
  ('planned', 'in_progress') ORDER BY lane DESC, id ASC`.
- Issue state refresh queries `story` table by story ID.
- Terminal states: `implemented`, `retired`.
- `story_id` is used as `issue.identifier`.
- `story.title` maps to `issue.title`.
- `story.lane` maps to `issue.lane` directly (no intake classification needed).

### 11.3 Normalization

All tracker backends MUST produce the normalized issue model from §4.1.1.

### 11.4 Tracker Writes

Inherited from Symphony: writes are agent-side, not orchestrator-side.

## 12. Prompt Construction and Context Assembly

### 12.1 Inputs (Extended)

- `workflow.prompt_template`
- Normalized `issue` object with Harness extensions.
- `attempt` (integer or null)
- Harness context assembly (see §12.3).

### 12.2 Rendering Rules

Inherited from Symphony (strict variable/filter checking).

### 12.3 Harness Context Assembly — NEW

Before rendering the prompt, the orchestrator assembles the Harness context
document based on the classified lane and the current context phase (intake
phase for first run, implementation phase for continuation runs).

Assembly algorithm:

```text
function assemble_harness_context(lane, phase, issue, workspace):
  docs = []

  // Always included ("Must in all lanes")
  docs.append(read(workspace / "AGENTS.md"))
  docs.append(read(workspace / "docs/FEATURE_INTAKE.md"))
  docs.append(run("harness-cli query matrix"))

  // Lane-dependent (from docs/CONTEXT_RULES.md)
  if lane in ["normal", "high-risk"]:
    docs.append(read(workspace / "README.md"))
    docs.append(read(workspace / "docs/HARNESS.md"))

  if lane == "high-risk":
    docs.append(read(workspace / "docs/ARCHITECTURE.md"))
    docs.append(read(workspace / "docs/CONTEXT_RULES.md"))
    for decision in relevant_decisions(issue):
      docs.append(read(decision.path))

  // Story packet
  if issue.story_id:
    story_path = find_story_file(workspace, issue.story_id)
    if story_path:
      docs.append(read(story_path))

  // Product docs when behavior changes
  if phase in ["planning", "implementation"] and lane != "tiny":
    for doc in affected_product_docs(issue):
      docs.append(read(doc))

  return join(docs, separator="\n---\n")
```

### 12.4 Retry/Continuation Semantics

`attempt` SHOULD be passed to the template. The Harness context SHOULD shift
from intake phase to implementation phase on continuation runs.

## 13. Logging, Status, and Observability

### 13.1 Logging Conventions (Extended)

REQUIRED context fields:

- `issue_id`
- `issue_identifier`
- `session_id`
- `lane` — Classified risk lane.
- `story_id` — When linked.
- `intake_id` — When recorded.

### 13.2 Harness-Specific Observability

In addition to standard Symphony observability:

- **Trace Quality Dashboard**: Running average of trace scores, broken down
  by lane. Alert when scores drop below lane requirements.
- **Verification Pass Rate**: Percentage of completed stories whose
  `harness-cli story verify` passed.
- **Friction Heatmap**: Most frequent friction patterns grouped by Harness
  component (`docs/HARNESS_COMPONENTS.md`).
- **Entropy Score Trend**: Track `harness-cli audit` entropy score over time.
- **Lane Distribution**: Percentage of work in each risk lane.
- **Context Score Distribution**: How well agents follow
  `docs/CONTEXT_RULES.md`.
- **Improvement Pipeline**: Open backlog items, pending proposals, outcome
  loop completion rate.

### 13.3 Runtime Snapshot (Extended)

The snapshot SHOULD include Harness metrics alongside standard Symphony fields:

```json
{
  "generated_at": "2026-06-09T12:00:00Z",
  "counts": {
    "running": 3,
    "retrying": 1,
    "by_lane": {"tiny": 1, "normal": 1, "high-risk": 1}
  },
  "harness_metrics": {
    "avg_trace_score": 2.4,
    "verification_pass_rate": 0.87,
    "entropy_score": 3,
    "open_friction_items": 5,
    "pending_proposals": 2,
    "traces_since_last_audit": 12,
    "maturity_level": "H3"
  },
  "running": [ ... ],
  "retrying": [ ... ],
  "agent_totals": { ... },
  "rate_limits": null
}
```

### 13.4 OPTIONAL HTTP Server Extension

Inherited from Symphony (§13.7) with additional endpoints:

- `GET /api/v1/harness/metrics` — Returns Harness-specific metrics (trace
  scores, verification rates, friction summary, entropy score).
- `GET /api/v1/harness/friction` — Returns recent friction items grouped by
  component.
- `GET /api/v1/harness/proposals` — Returns pending improvement proposals.
- `POST /api/v1/harness/audit` — Triggers an immediate audit cycle.
- `POST /api/v1/harness/propose` — Triggers immediate proposal generation.

## 14. Failure Model and Recovery Strategy

### 14.1 Failure Classes (Extended)

Inherited from Symphony:

1. Workflow/Config Failures
2. Workspace Failures
3. Agent Session Failures
4. Tracker Failures
5. Observability Failures

Harness-specific failure classes:

6. `Intake Classification Failures`
   - Intake classifier cannot determine lane.
   - Harness CLI not available.
   - `harness.db` corrupted or inaccessible.

7. `Trace Recording Failures`
   - `harness-cli trace` command fails.
   - Trace does not meet minimum tier requirements.

8. `Verification Gate Failures`
   - `harness-cli story verify` command fails.
   - Verification command not configured for the linked story.

9. `Improvement Pipeline Failures`
   - `harness-cli propose` or `harness-cli audit` fails.
   - Backlog write failure.

### 14.2 Recovery Behavior (Extended)

Inherited from Symphony, plus:

- Intake classification failure: skip this issue for this tick, retry on next
  poll.
- Trace recording failure: log warning, record failure metadata in
  orchestrator state, do not block completion.
- Verification failure: mark run as `SucceededWithWarnings`, notify operator.
- Improvement pipeline failure: log warning, continue operating.

### 14.3 Partial State Recovery (Extended)

After restart:

- Standard Symphony recovery (poll tracker, reuse workspaces).
- Query `harness.db` for recent operational state.
- Detect orphaned in-progress stories and log advisory.
- Run `harness-cli audit` to establish post-restart entropy baseline.

## 15. Security and Operational Safety

Inherited from Symphony (§15) with one addition:

- `harness.db` contains operational metadata, not secrets. However,
  implementations SHOULD restrict filesystem access to prevent agents from
  tampering with other issues' trace records or story status.
- High-risk lane work SHOULD use stricter approval policies as configured
  in `harness.lane_approval`.

## 16. Reference Algorithms

### 16.1 Service Startup

```text
function start_service():
  configure_logging()
  start_observability_outputs()
  start_workflow_watch(on_change=reload_workflow)

  verify_harness_cli_available()
  harness_cli("init")  // Ensure harness.db exists
  harness_cli("migrate")  // Apply pending migrations

  state = initialize_orchestrator_state()

  validation = validate_dispatch_config()
  if validation is not ok:
    fail_startup(validation)

  startup_terminal_workspace_cleanup()
  baseline_entropy = harness_cli("audit")
  state.entropy_score = baseline_entropy

  schedule_tick(delay_ms=0)
  event_loop(state)
```

### 16.2 Intake-Aware Dispatch

```text
function dispatch_with_intake(issue, state):
  // Classify through intake gate
  if harness.auto_intake and issue.lane is null:
    classification = classify_intake(issue)
    if classification failed:
      log_intake_failure(issue)
      return state  // Skip, retry next tick

    issue.lane = classification.lane
    issue.risk_flags = classification.flags
    issue.intake_id = harness_cli("intake",
      type=classification.input_type,
      summary=issue.title,
      lane=classification.lane)
    issue.input_type = classification.input_type

  // Check lane concurrency
  if lane_slots_exhausted(state, issue.lane):
    return state

  // Set lane-appropriate approval policy
  approval = resolve_approval_policy(issue.lane)

  // Dispatch
  return dispatch_issue(issue, state, attempt=null, approval=approval)
```

### 16.3 Post-Run Harness Lifecycle

```text
function harness_post_run(issue, session, workspace, state):
  // 1. Record trace
  trace_id = harness_cli("trace",
    summary=session.summary,
    outcome=session.outcome,
    story=issue.story_id,
    intake=issue.intake_id,
    agent=config.agent.kind,
    actions_taken=session.actions,
    files_read=session.files_read,
    files_changed=session.files_changed,
    harness_friction=session.friction)

  // 2. Score trace
  trace_score = harness_cli("score-trace", id=trace_id)
  state.trace_scores.update(trace_score)

  // 3. Score context
  if config.harness.context_scoring:
    harness_cli("score-context", trace_id)

  // 4. Verify stories
  verification_passed = null
  if config.harness.verify_before_complete and issue.story_id:
    verification_passed = harness_cli("story verify", issue.story_id)

  // 5. Collect friction
  if session.friction and session.friction != "none":
    state = accumulate_friction(state, session.friction)
    if friction_threshold_reached(state, session.friction):
      harness_cli("backlog add",
        title=summarize_friction(session.friction),
        pain=session.friction)

  // 6. Check proposal interval
  if state.completed_trace_count % config.harness.propose_interval == 0:
    harness_cli("propose")

  // 7. Check audit interval
  if state.completed_trace_count % config.harness.audit_interval == 0:
    state.entropy_score = harness_cli("audit")

  return {trace_id, trace_score, verification_passed}
```

## 17. Test and Validation Matrix

### 17.1 Core Conformance (Inherited)

All Symphony core conformance tests from Symphony SPEC §17.1-17.7.

### 17.2 Harness Conformance (New)

- `harness.auto_intake` causes automatic intake classification before dispatch.
- Intake classification records a durable `intake` row via Harness CLI.
- Lane is correctly derived from risk flag count.
- `harness.lane_concurrency` limits are enforced.
- `harness.lane_approval` overrides agent approval policy per lane.
- Workspace creation runs `harness-cli init` for new workspaces.
- Post-run lifecycle records a trace via `harness-cli trace`.
- Post-run trace is scored against `docs/TRACE_SPEC.md` tier requirements.
- Context scoring runs after trace recording when enabled.
- Story verification runs after trace recording when enabled.
- Friction accumulator correctly increments and triggers backlog creation.
- Proposal generation runs at configured interval.
- Audit runs at configured interval and records entropy score.
- Startup recovery queries `harness.db` for orphaned stories.
- `tracker.kind == "harness_backlog"` reads candidates from the story table.
- Harness context assembly follows `docs/CONTEXT_RULES.md` for each lane.
- `SucceededWithWarnings` state is used when verification or trace quality
  falls below lane requirements.

### 17.3 Real Integration Profile

- All Symphony real integration checks.
- Real Harness CLI smoke test with `harness-cli init`, `harness-cli intake`,
  `harness-cli trace`, and `harness-cli story verify`.
- End-to-end test: create a story, dispatch it, verify the agent records a
  trace, and the trace meets the lane's quality tier.

## 18. Implementation Checklist (Definition of Done)

### 18.1 REQUIRED for Conformance

Everything from Symphony SPEC §18.1, plus:

- Harness CLI detection and initialization in workspace setup.
- Intake classification before dispatch (when `harness.auto_intake` is true).
- Lane-based prompt context assembly per `docs/CONTEXT_RULES.md`.
- Post-run trace recording via `harness-cli trace`.
- Post-run trace scoring via `harness-cli score-trace`.
- Story verification gate via `harness-cli story verify`.
- Friction collection with configurable threshold.
- Startup recovery from `harness.db`.
- Structured logs include Harness context fields (lane, story_id, intake_id).

### 18.2 RECOMMENDED Extensions

Everything from Symphony SPEC §18.2, plus:

- `tracker.kind == "harness_backlog"` support.
- Context scoring via `harness-cli score-context`.
- Periodic `harness-cli propose` and `harness-cli audit`.
- Harness-specific HTTP API endpoints.
- Per-lane concurrency and approval configuration.
- Multi-agent support (Codex, Claude Code, Cursor, Devin).
- Maturity target monitoring and warnings.

### 18.3 Operational Validation

Everything from Symphony SPEC §18.3, plus:

- Verify Harness CLI binary works on the target platform.
- Verify `harness.db` schema is current (run `harness-cli migrate`).
- Verify trace recording and scoring produces expected output.
- Verify story verification commands execute correctly.
- Run `harness-cli audit` and confirm entropy score is below acceptable
  threshold.

## Appendix A. Concept Mapping: Symphony → Harness Symphony

| Symphony Concept | Harness Symphony Equivalent | Notes |
| --- | --- | --- |
| `WORKFLOW.md` | `WORKFLOW.md` + Harness docs hierarchy | Prompt template extended with Harness context assembly |
| Issue (from Linear) | Issue + Harness intake classification + story linkage | Enriched with lane, risk flags, story_id, intake_id |
| Workspace (bare directory) | Workspace with Harness installed (CLI, docs, db) | Every workspace is a Harness-enabled project |
| In-memory orchestrator state | SQLite-backed state + in-memory scheduling | `harness.db` provides restart recovery |
| Agent subprocess logs | Harness execution traces (`harness-cli trace`) | Structured, scored, queryable records |
| Retry backoff | Lane-aware retry backoff | High-risk gets longer delays, tiny gets shorter |
| Concurrency limits | Lane-aware concurrency limits | Per-lane dispatch control |
| Hook scripts | Harness lifecycle hooks (init, intake, trace, verify) | Default hooks implement Harness operations |
| Observability (logs only) | Traces + context scores + entropy audits + friction pipeline | Harness provides multi-dimensional observability |
| No post-run verification | Story verification gates | Mechanical proof before completion |
| No improvement loop | Friction → backlog → propose → implement → outcome | Self-improving operating environment |
| Single agent (Codex) | Multi-agent support (Codex, Claude, Cursor, Devin) | Agent-neutral runner with adapter pattern |

## Appendix B. Harness Maturity Integration

Harness Symphony supports the Harness Maturity Ladder
(`docs/HARNESS_MATURITY.md`). The orchestrator's operational behavior changes
based on the configured `harness.maturity_target`:

| Maturity Level | Symphony Behavior |
| --- | --- |
| H0 | No Harness integration. Behaves like vanilla Symphony. |
| H1 | Static Harness docs in workspace. No durable tracking. |
| H2 | Full durable layer (intake, stories, traces). Intake classification. Trace recording. |
| H3 | Active observability: trace scoring, context scoring, friction pipeline, backlog proposals. |
| H4 | Verification gates required. Story proof commands enforce completion criteria. Audit checks run automatically. |
| H5 | Self-improving: friction auto-creates backlog items, proposals auto-commit when confidence is high, maturity metrics are continuously monitored. |

The default behavior targets H3-H4, which balances structured operations with
practical automation.

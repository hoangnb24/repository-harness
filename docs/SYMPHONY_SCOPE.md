# Harness Symphony Revised Scope

Status: proposed replacement scope (revision 2)

Audience: `repository-harness` maintainers, Harness CLI implementers, and
coding-agent runtime integrators.

Supersedes: the broader Symphony proposal from PR #16 and revision 1 of this
document.

Revision 2 changes:

- Changesets become the primary record (an operation log written by
  `harness-cli` as it executes), not a derived diff of two SQLite files.
- `harness.db` becomes a rebuildable local index over committed changesets.
- Per-PR manual reconciliation is replaced by an idempotent `sync` command.
- `HARNESS_DB_PATH` support in `harness-cli` is a hard prerequisite (v0).
- Changesets must be rendered human-readable in the run summary.
- Run ceremony is lane-aware; tiny-lane work gets a lightweight path.
- The standalone queue milestone is removed; a single active-run lock is
  enough until real concurrency arrives.
- Local run artifacts get an explicit retention policy.

## 1. Product Thesis

Harness Symphony should not start as a full agent-orchestration platform.

It should start as a safe local agent workbench that turns Harness stories into
isolated, reviewable agent runs.

The useful promise is:

```text
Harness story
  -> isolated worktree
  -> copied harness.db
  -> explicit agent run contract
  -> validation/result artifact
  -> committed changeset (operation log)
  -> optional PR
  -> idempotent sync after merge
```

This is narrower than OpenAI Symphony. OpenAI Symphony makes an issue tracker
the control plane for continuous autonomous implementation. Harness Symphony can
grow toward that model, but the first version should prove the Harness-specific
loop before adding daemon scheduling, external issue trackers, concurrent
agents, or automatic repair.

## 2. Why This Belongs In repository-harness

`repository-harness` already defines the agent operating system:

- intake and risk lanes
- context loading rules
- story and proof records
- trace and friction records
- verification commands
- drift/audit/proposal loops

The missing layer is execution isolation. Today an agent or human can follow the
Harness workflow, but the repository does not provide a repeatable way to:

- prepare a safe workspace for one story
- prevent accidental root `harness.db` mutation
- hand an agent a precise run contract
- capture run outcome in machine-readable form
- preserve useful artifacts for review
- update durable state only after human acceptance

Harness Symphony should fill that gap.

## 3. Design Principles

### 3.1 Symphony Is Not A Second Harness Brain

Symphony must not deeply classify product work, decide implementation strategy,
assemble all task context, or replace `harness-cli`.

Harness owns:

- product intake
- risk lane policy
- story scope
- context rules
- validation expectations
- traces
- durable project memory

Symphony owns:

- run preparation
- workspace isolation
- copied database wiring
- agent launch contract
- run status and logs
- run result collection
- optional PR creation
- post-merge sync support

### 3.2 The First Version Optimizes Trust, Not Throughput

The first useful version is not a daemon. It is a deterministic local runner
that humans and agents can understand.

Throughput features such as auto-polling, external work sources, multiple
active agents, and CI repair should wait until the local run contract is proven.

### 3.3 Committed Changesets Are The Source Of Truth

This is the keystone principle of revision 2.

`harness.db` is a local index, not the source of truth. The source of truth is
the ordered set of committed changesets under `.harness/changesets/`.

Consequences:

- `harness-cli` appends each durable operation to the run's changeset as it
  executes. The changeset is an operation log, not a diff.
- Symphony never diffs SQLite files to produce a changeset.
- Any clone can rebuild `harness.db` by replaying committed changesets:

  ```bash
  harness-cli db rebuild --from .harness/changesets
  ```

- Post-merge reconciliation collapses into an idempotent replay of
  committed-but-unapplied changesets (`harness-symphony sync`, see 4.10).
- Multiple team members can land Symphony PRs without coordinating around a
  single machine's `harness.db`.

This removes the riskiest parts of the previous scope: base-checksum
validation, per-PR reconcile bookkeeping, and `reconciliation_failed` repair
flows that depended on diffing database states.

### 3.4 Review Artifacts And Committed State

The reviewable collaboration surface is split by durability:

- run summaries (with a human-readable changeset rendering) stay local and feed
  the PR body
- run results stay local for Web UI review and debugging
- semantic Harness changesets are committed durable state
- docs, stories, decisions, tests, and product changes

`harness.db` itself is never committed and never reviewed.

### 3.5 Ceremony Must Match The Risk Lane

Harness already classifies work into `tiny`, `normal`, and `high_risk` lanes.
Symphony must not impose the full worktree + contract + result + changeset +
sync loop on work the harness itself calls tiny.

- `normal` and `high_risk` lanes: full isolated-run loop.
- `tiny` lane: a lightweight path is allowed (see 4.11).

If users experience Symphony as bureaucracy around small tasks, they will stop
using it for large ones.

## 4. Revised v1 Scope

v1 is a safe on-demand runner.

### v0 Prerequisite: harness-cli Database Path And Operation Log

Two `harness-cli` capabilities are hard prerequisites and must land before any
Symphony code:

1. `harness-cli` must respect `HARNESS_DB_PATH`. Without this, copied-database
   isolation does not exist and every other guarantee in this document is
   fiction.
2. `harness-cli` must support an operation-log mode: when `HARNESS_RUN_ID` is
   set, every durable write is also appended as a semantic operation to

   ```text
   .harness/changesets/<run_id>.changeset.jsonl
   ```

   in the workspace. The log is written transactionally with the database
   write: either both happen or neither does.

### Required v1 Capabilities

#### 4.1 Doctor

Command:

```bash
harness-symphony doctor
```

Checks:

- Git is available.
- Git worktrees are supported.
- repository root is discoverable.
- `harness.db` exists or can be rebuilt from committed changesets.
- `harness-cli` exists, supports `HARNESS_DB_PATH`, and supports the
  operation log.
- `.gitignore` protects local DB and Symphony runtime files.
- configured agent adapter exists.
- configured PR adapter is available only if PR creation is enabled.

Doctor output should be actionable. Each failure should include the next command
or configuration change required to fix it.

#### 4.2 Work List

Command:

```bash
harness-symphony work list
```

Shows Harness work that can be run:

```text
ID      Status       Lane       Verify      Runnable  Reason
US-015  planned      normal     configured  yes       ready
US-016  in_progress  normal     missing     warn      proof command missing
```

v1 should align with the current `story.status` schema:

```text
planned
in_progress
implemented
changed
retired
```

If Symphony needs blocked, needs-intake, in-review, or done semantics, it must
add an explicit schema migration or store those states in a separate run/result
record. It must not silently assume statuses that the Harness database does not
support.

#### 4.3 Prepare Run

Command:

```bash
harness-symphony run <story-id> --prepare-only
```

Creates:

```text
.symphony/worktrees/<run_id>/
.symphony/runs/<run_id>/RUN_CONTRACT.json
```

The root working tree is never used as the agent workspace.

The copied database is the only database the run should mutate. Symphony should
set:

```bash
HARNESS_DB_PATH=<worktree>/harness.db
HARNESS_RUN_ID=<run_id>
HARNESS_RUN_MODE=execute
```

With the operation log in place, no base database snapshot is required. The
changeset accumulates inside the worktree as the agent works and is committed
with product/docs/test changes. Run summaries and results remain local runtime
artifacts.

#### 4.4 Run Contract

Each run must have a machine-readable contract:

```json
{
  "version": 1,
  "run_id": "run_123",
  "mode": "execute",
  "story_id": "US-015",
  "worktree": ".symphony/worktrees/run_123",
  "harness_db_path": ".symphony/worktrees/run_123/harness.db",
  "required_outputs": [
    ".harness/runs/run_123/SUMMARY.md",
    ".harness/runs/run_123/RESULT.json"
  ],
  "forbidden_paths": [
    "harness.db",
    ".symphony/state.db",
    ".symphony/worktrees/**"
  ],
  "agent_instructions": [
    "Follow AGENTS.md and Harness docs.",
    "Implement only the assigned story scope.",
    "Use the copied harness.db.",
    "Run the configured verification command when available."
  ]
}
```

This contract is for agents first and humans second. It should remove ambiguity
about where the agent is allowed to work and what it must produce.

In addition to the JSON file, Symphony must surface the same contract through
the worktree's `AGENTS.md` shim. `AGENTS.md` is the entry point coding agents
reliably read first; the run contract must be visible there, not only in a
path the agent may never open. The shim insert should be a short block linking
to `RUN_CONTRACT.json` and restating the assigned story, the database path,
the required outputs, and the forbidden paths.

#### 4.5 Agent Launch

Command:

```bash
harness-symphony run <story-id>
```

v1 may support one default local agent adapter plus a custom command adapter.

Configuration example:

```yaml
agent:
  adapter: codex
```

The Codex adapter speaks the `codex app-server` JSON-RPC protocol. The
`claudecode` adapter drives Claude Code headless (`claude -p ... --output-format
stream-json`), a one-shot process whose terminal `result` event decides success.
The `custom` adapter remains available for one-shot command adapters, but named
adapters (Codex, Claude Code) are preferred over command-string conventions.
Harness is meant to support multiple coding agents.

Named adapters also report setup readiness (binary presence and a heuristic auth
check) through `doctor` and the Web UI, so users can see which agents are ready
before launching a run.

#### 4.6 Finish Protocol

Agents should not signal success only by exiting.

Required output:

```text
.harness/runs/<run_id>/RESULT.json
```

Example:

```json
{
  "version": 1,
  "run_id": "run_123",
  "story_id": "US-015",
  "outcome": "completed",
  "validation": {
    "commands": [
      {
        "command": "cargo test --workspace",
        "result": "pass"
      }
    ]
  },
  "changed_files": [
    "crates/harness-cli/src/interface.rs"
  ],
  "summary_path": ".harness/runs/run_123/SUMMARY.md",
  "changeset_path": ".harness/changesets/run_123.changeset.jsonl"
}
```

Allowed v1 outcomes:

```text
completed
blocked
needs_intake
partial
failed
cancelled
```

`blocked` and `needs_intake` are run outcomes in v1. They should not be written
into `story.status` unless the Harness schema explicitly supports them.

#### 4.7 Local Status

Command:

```bash
harness-symphony runs list
harness-symphony runs show <run_id>
```

Shows:

- run id
- story id
- branch
- worktree
- status
- result path
- PR URL if created
- sync status (changeset applied locally or not)
- next human action

`harness-symphony status` must make committed-but-unapplied changesets obvious
(see 4.10).

#### 4.8 Optional PR Creation

PR creation should be configurable, not mandatory for every run.

```yaml
pull_request:
  create: ask
  draft_for:
    - blocked
    - needs_intake
    - partial
```

Recommended v1 policy:

- completed implementation: open normal PR
- intake-only: open draft PR
- blocked/needs-intake: open draft PR only if useful artifacts exist
- failed/cancelled: no PR by default

If a PR is created, it must use the summary as the PR body and commit the
semantic changeset:

```text
.harness/changesets/<run_id>.changeset.jsonl
```

#### 4.9 Semantic Changesets

Changesets are semantic Harness operations, appended by `harness-cli` as the
operations execute (see v0 prerequisite). Raw SQLite diffs are never used.

```jsonl
{"op":"changeset.header","version":1,"run_id":"run_123","base_schema_version":4}
{"op":"story.update","id":"US-015","payload":{"status":"in_progress"}}
{"op":"trace.add","payload":{"story_id":"US-015","outcome":"completed"}}
```

Each operation must be:

- stable
- idempotent (replaying an applied changeset is a no-op)
- schema-versioned
- ordered within the changeset
- applyable through `harness-cli`, not direct SQL

Because the log is written at execution time, operation intent and order are
preserved exactly. There is no generation step to defer and no diffing
algorithm to maintain.

Human-readable rendering: raw JSONL is a hostile review surface. Symphony must
render the changeset into a markdown section of `SUMMARY.md` (and therefore the
PR body), for example:

```markdown
## Harness Changes

| Operation    | Entity | Change                              |
| ------------ | ------ | ----------------------------------- |
| story.update | US-015 | status: planned -> in_progress      |
| trace.add    | US-015 | outcome: completed                  |
| decision.add | D-031  | "Use operation log for changesets"  |
```

Reviewers approve the rendered table; the JSONL is the machine record.

#### 4.10 Sync

There is no per-PR `reconcile <pr-number>` command. It is replaced by:

```bash
harness-symphony sync
```

Behavior:

1. Scan `.harness/changesets/` on the current checkout (typically `main` after
   pulling).
2. Compare against the applied-changeset log in `.symphony/state.db` (and a
   `changeset_applied` record inside `harness.db`).
3. Replay every committed-but-unapplied changeset, in commit order, through
   `harness-cli` in a single transaction per changeset.
4. Record each applied changeset id.

Properties:

- Idempotent: running `sync` twice is safe; applied changesets are skipped.
- Author-independent: it applies teammates' merged changesets, not only runs
  started on this machine.
- Clone-friendly: on a fresh clone, `sync` (or `harness-cli db rebuild`) can
  reconstruct `harness.db` entirely from committed history.
- Drift-resistant: `harness-symphony status` and `doctor` must warn when
  committed changesets are unapplied, so a forgotten `sync` is loud, not
  silent.

A merged PR whose changeset has not been synced leaves root `harness.db`
stale but never corrupted. A closed-unmerged PR requires no action at all: its
changeset was never committed to `main`, so it is never applied.

If applying an operation fails (schema mismatch, conflicting state), `sync`
must stop at that changeset, leave the database transactionally intact, report
the failing operation, and continue to be safe to re-run after repair.

#### 4.11 Tiny-Lane Lightweight Path

For stories the harness classifies as `tiny`, Symphony may offer:

```bash
harness-symphony run <story-id> --here
```

Behavior:

- no worktree; the run executes in the current checkout
- `HARNESS_DB_PATH` still points at a copied database in `.symphony/runs/`
- the operation log, `RESULT.json`, and summary are still required
- the run is flagged `lightweight` in run state and in the summary

The database isolation and finish protocol are non-negotiable; only the
worktree ceremony is waived. `--here` must refuse `normal` and `high_risk`
stories.

#### 4.12 Artifact Retention

Local run artifacts grow with every run. v1 must define retention up front:

- `.harness/changesets/` is permanent history. It is the source of truth and
  is never pruned.
- `.harness/runs/<run_id>/` (summary, result) is local runtime evidence, kept by
  default, with a compaction command:

  ```bash
  harness-symphony runs compact --keep-last <n>
  ```

  Compaction may fold old summaries into a single archive file or delete them,
  but must never touch `.harness/changesets/`.
- `.symphony/` runtime state (worktrees, logs, state db) is local, ignored,
  and freely cleanable.

## 5. v1 Non-Goals

Do not include these in v1:

- automatic work polling
- multiple active runs
- a run request queue (a single active-run lock is sufficient; see 7)
- Linear, GitHub Issues, Jira, or external work-source adapters
- hosted dashboard
- webhook-triggered sync
- CI repair mode
- review-comment repair mode
- automatic PR merge
- multi-agent planning
- raw SQLite merge through Git
- SQLite diffing of any kind

These are future features after the local workbench is useful.

## 6. v2 Scope: Reviewable PR Runner

Add after v1 proves that agents can complete local isolated runs.

Required:

- PR creation adapter
- draft/open PR policy
- changeset rendering in PR body
- `sync` hardening (conflict reporting, partial-failure recovery)
- unapplied-changeset detection in `status` and `doctor`
- branch and worktree cleanup command
- `harness-cli db rebuild --from .harness/changesets`

Commands:

```bash
harness-symphony pr create <run_id>
harness-symphony pr retry <run_id>
harness-symphony sync
harness-symphony status
```

Acceptance:

- a completed run can become a PR
- after merge and pull, `sync` updates root `harness.db` from the committed
  changeset
- a closed-unmerged PR requires no cleanup of durable state
- `status` shows committed-but-unapplied changesets
- a fresh clone can rebuild `harness.db` from committed changesets

## 7. v3 Scope: Symphony-Style Automation

This is where the project starts to resemble OpenAI Symphony, and the first
place a queue is justified.

Required:

- auto-mode
- polling Harness work source
- policy-driven eligibility
- run request queue and retry semantics (introduced here, where concurrency
  and unattended operation actually need them)
- external work-source adapter interface
- bounded concurrency if run isolation is proven

Potential adapters:

```text
HarnessDbWorkSource
GitHubIssueWorkSource
LinearWorkSource
JiraWorkSource
RemoteHarnessWorkSource
```

The adapter boundary should not change run contracts, result files, workspace
isolation, or sync semantics.

Implemented command:

```bash
harness-symphony auto --enable
```

`--enable` is required on every invocation so unattended polling is explicitly
opt-in. `HarnessDbWorkSource` is the first implemented source. External sources
such as GitHub Issues, Linear, Jira, and remote Harness are recognized as
adapter boundaries for future integrations and do not change the run contract,
result files, changesets, or sync semantics.

The existing single active-run lock in `.symphony/state.db` remains the
concurrency guard for this first automation slice. The queue controls
unattended eligibility and retry attempts; it does not introduce multiple
active agents by itself.

## 8. Architecture Boundaries

Suggested crates:

```text
crates/
  harness-core/
    domain/
    ports/
    use_cases/

  harness-cli/
    existing durable-layer CLI
    HARNESS_DB_PATH support
    operation-log writing
    changeset apply and rebuild commands

  harness-symphony/
    cli/
    config/
    adapters/
    orchestration/
```

Dependency direction:

```text
harness-symphony -> harness-core
harness-cli      -> harness-core
harness-core     -> no infrastructure dependencies
```

Do not split crates before the first implementation needs shared domain code.
If the MVP can be implemented cleanly in one crate first, prefer the smaller
change.

## 9. Configuration

Path:

```text
.harness/symphony.yml
```

Example:

```yaml
version: 1

repo:
  root: "."
  harness_db: "harness.db"

symphony:
  state_db: ".symphony/state.db"
  runs_dir: ".harness/runs"
  worktrees_dir: ".symphony/worktrees"
  single_active_run: true

agent:
  adapter: codex        # or: claudecode, custom
  model: sonnet         # optional; used by named adapters (e.g. Claude Code)
  timeout_minutes: 10

pull_request:
  create: ask
  provider: github
  draft_for:
    - blocked
    - needs_intake
    - partial

changeset:
  directory: ".harness/changesets"
  render_in_summary: true

runs:
  allow_here_for_tiny: true
  compact_keep_last: 50

auto:
  source: harness-db
  poll_interval_seconds: 30
  max_attempts: 3

cleanup:
  keep_failed_worktrees: true
  cleanup_after_sync: false
```

## 10. Git Ignore Requirements

Must ignore:

```gitignore
harness.db
harness.db-wal
harness.db-shm
.symphony/
```

Must not ignore:

```gitignore
.harness/runs/*/SUMMARY.md
.harness/runs/*/RESULT.json
.harness/changesets/
```

## 11. Acceptance Criteria

### 11.1 Prerequisite Acceptance

Given `HARNESS_DB_PATH` points at a non-default database, every `harness-cli`
durable command reads and writes that database only.

Given `HARNESS_RUN_ID` is set, every `harness-cli` durable write appends a
matching semantic operation to the run changeset, atomically with the write.

### 11.2 MVP Acceptance

Given an eligible story exists in `harness.db`, when a user runs:

```bash
harness-symphony run <story-id> --prepare-only
```

then Symphony:

1. refuses to use the root checkout as the run workspace
2. creates a dedicated worktree
3. copies `harness.db`
4. writes `RUN_CONTRACT.json`
5. surfaces the run contract in the worktree `AGENTS.md` shim
6. exports `HARNESS_DB_PATH`, `HARNESS_RUN_ID`, and `HARNESS_RUN_MODE`
7. leaves root `harness.db` unchanged

### 11.3 Agent Result Acceptance

Given an agent run finishes, Symphony accepts the run only if:

1. `SUMMARY.md` exists
2. `RESULT.json` exists
3. `RESULT.json` has a valid outcome
4. required validation evidence is present or explicitly marked unavailable
5. forbidden local runtime files are not staged for commit

### 11.4 PR Acceptance

Given PR creation is enabled, Symphony:

1. uses the summary as the PR body and commits the changeset artifact
2. renders the changeset as a markdown table in the summary and PR body
3. does not include `harness.db`
4. does not include `.symphony/` files

### 11.5 Sync Acceptance

Given `main` contains merged changesets that are not yet applied locally, when
the user runs:

```bash
harness-symphony sync
```

then Symphony:

1. detects all committed-but-unapplied changesets
2. applies them in commit order, transactionally, through `harness-cli`
3. records each applied changeset id
4. is a no-op when run again
5. on failure, leaves `harness.db` intact, reports the failing operation, and
   remains safe to re-run

Given a fresh clone with no `harness.db`, `harness-cli db rebuild` (or `sync`)
reconstructs the database from committed changesets.

### 11.6 Tiny-Lane Acceptance

Given a `tiny`-lane story, `run --here` executes without a worktree but still
uses a copied database, writes the operation log, and produces `RESULT.json`.

Given a `normal` or `high_risk` story, `run --here` is refused.

## 12. Product Risks

### 12.1 Too Much Ceremony

Risk: a user sees Symphony as bureaucracy around simple coding tasks.

Mitigation:

- make `doctor`, `work list`, and `run --prepare-only` excellent
- keep PR creation optional
- default blocked/intake-only PRs to draft
- provide the tiny-lane `--here` path

### 12.2 Database State Confusion

Risk: users do not know whether `harness.db`, docs, or changesets are the source
of truth.

Mitigation:

- committed changesets are the source of truth, by definition (3.3)
- `harness.db` is rebuildable and documented as an index
- `status` and `doctor` surface unapplied changesets loudly

### 12.3 Agent Adapter Lock-In

Risk: a Harness-native tool becomes Codex-only.

Mitigation:

- make Codex the first adapter, not the core model
- ship a Claude Code adapter alongside Codex to keep the adapter boundary honest
- support custom command adapters in v1
- keep agent protocol file-based where possible

### 12.4 Operation-Log Drift

Risk: the operation log and the database disagree because a write path bypassed
the log.

Mitigation:

- all durable writes go through `harness-cli`; direct SQL is unsupported
- log append and database write are transactional (v0 prerequisite)
- `doctor` can verify that replaying changesets reproduces the current
  database state

### 12.5 Artifact Growth

Risk: local run artifacts bloat the checkout over time.

Mitigation:

- retention policy and `runs compact` from v1 (4.12)
- only changesets stay permanent in git; they are small, append-only JSONL

## 13. Recommended Implementation Order

1. Add `HARNESS_DB_PATH` support to `harness-cli`.
2. Add operation-log writing to `harness-cli`.
3. Add `harness-cli db changeset apply` (idempotent replay).
4. Add `harness-symphony doctor`.
5. Add config loading and path normalization.
6. Add run state store with single active-run lock.
7. Add worktree creation and copied DB wiring.
8. Add `RUN_CONTRACT.json` and the `AGENTS.md` shim insert.
9. Add `RESULT.json` validation.
10. Add custom command agent adapter.
11. Add `runs list/show` and `status`.
12. Add changeset rendering in `SUMMARY.md`.
13. Add optional PR creation.
14. Add `harness-symphony sync`.
15. Add `harness-cli db rebuild` and tiny-lane `--here`.
16. Add auto-mode, queue, and external work-source adapters (v3).

## 14. One-Sentence Positioning

Harness Symphony is a safe agent workbench for turning Harness stories into
isolated, reviewable runs whose durable state lives in committed changesets; it
can become a Symphony-style autonomous orchestrator only after that local loop
is trusted.

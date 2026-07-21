# Superseded Phase 5 Evolution Infrastructure Roadmap

> Historical compatibility roadmap. This is the pre-reduction Phase 5 plan for
> maturity scoring, audits, interventions, proposals, and batch verification.
> It is preserved for CLI/state provenance and is not the current reduction
> Phase 5 or the default repository workflow.

# Phase 5 — Evolution Infrastructure: Finalized Scope

> Historical compatibility roadmap. Its phase numbering predates decisions
> 0019 and 0020 and is not the active repository-centered roadmap. The Rust
> CLI/SQLite workflow it describes remains available only through explicit
> compatibility selection. See `PHASE3.md` for the active phase.

**Target repo:** `repository-harness` (feature branch off `main`)
**Validation:** `harness-benchmark` re-run after implementation
**Current harness maturity:** H4 partial (Phase 4 story verification + pre-close gate complete)
**Target maturity:** H4 (full) → H5 (partial: self-improvement loop, drift detection, batch verification)

---

## Phase 4 Confirmation

Phase 4 is implemented and merged to `main`. Evidence:

| Story | Status | Evidence |
|-------|--------|----------|
| US-012: Story `verify_command` field | Implemented | `002-story-verify.sql` migration; `story add --verify` and `story update --verify` work |
| US-015: Story verify command | Implemented | `story verify <id>` runs `verify_command`, records pass/fail |
| US-016: Auto trace scoring on write | Implemented | `trace` command auto-scores and prints tier summary |
| US-017: Pre-close verification gate | Implemented | `trace --story` warns when linked story verification hasn't passed |
| US-018: CLI UX hardening | Implemented | `--version`, accepted-value help, numeric proof hints, recovery messages |

The maturity ladder shows H4 as **partial** — batch verification and proof-column automation remain open.

---

## What Phase 5 Is

Phase 5 turns the harness from a system that *verifies individual stories* into one
that can *evolve itself*. Phase 4 gave agents mechanical proof for each story.
Phase 5 gives the harness the ability to:

1. **Complete H4** — batch verification across all stories.
2. **Start H5** — friction-to-proposal pipeline, drift detection,
   self-improvement protocol.
3. **Close remaining component gaps** — tool registry, intervention recording
   schema, context rule measurement.

The theme is **Validate → Check → Improve**:

```
Validate:  score-context (US-022) + audit (US-023) → "here's what's wrong"
Check:     verify-all (US-020) → "here's what's broken"
Improve:   propose (US-024) → "here's what to fix, based on patterns"
```

---

## Research Grounding

| Paper | Phase 5 Relevance |
|---|---|
| Runtime Substrate (2605.13357) | H5 = "the harness can propose safe improvements to itself" |
| Continual Harness (2605.09998) | Self-improvement requires verified traces + outcome comparison — Phase 4 provides the verification; Phase 5 adds the evolution loop |
| "The Last Harness" (2604.21003) | The Evolution role in Worker→Evaluator→Evolution must be mechanical and auditable |
| AHE (2604.25850) | Tool registry and capability manifest close the NexAU "Tool descriptions" gap |
| NLAHs (2603.25723) | Context rule enforcement needs measurement before it can be enforced |

---

## Why This Order Matters

```
US-019 Tool Registry
  ↓ machine-readable command manifest enables measurement and discovery
  ↓ closes the NexAU "Tool descriptions" gap
US-020 Batch Story Verification
  ↓ agents can verify all stories at once, completes H4
  ↓ the Evaluator role scales beyond single stories
US-021 Intervention Recording Schema
  ↓ human review events are separated from agent traces
  ↓ enables analysis of where humans override agent work
US-022 Context Rule Measurement
  ↓ measures whether agents actually follow context rules
  ↓ enables future enforcement and identifies over/under-reading
US-023 Drift Detection / Entropy Score
  ↓ stale docs, orphaned stories, and unlinked decisions are flagged
  ↓ enables the self-improvement proposal pipeline
US-024 Improvement Proposal Pipeline
  ↓ friction patterns become structured proposals with predicted impact
  ↓ the harness starts proposing its own backlog items — H5 begins
```

US-019 is first because the tool registry is needed for context measurement
(US-022) and provides the manifest that batch verification (US-020) can reference.
US-020 completes H4. US-021 is independent but unlocks better analysis. US-022
depends on having a manifest of what exists. US-023 depends on having structured
records to audit. US-024 depends on friction data (existing), drift data (US-023),
and intervention data (US-021) to compose proposals.

---

## Stories

### US-019: Machine-Readable Tool Registry

**Background:**

The NexAU cross-reference in `HARNESS_COMPONENTS.md` notes: "no standalone tool
schema or generated command reference." The CLI has `--help` output, but agents
cannot programmatically discover available commands, their arguments, or which
harness responsibilities they serve. Additionally, no mechanism exists for
registering non-harness-cli tools (project scripts, custom CLIs, etc.).

**Reason:**

AHE (arXiv:2604.25850) calls for explicit capability manifests. Context
measurement (US-022) needs to know what tools exist to measure whether agents use
the right ones.

**Solution:**

1. New file `docs/TOOL_REGISTRY.md` — human-readable command reference generated
   from CLI help, grouped by responsibility.
2. New command `harness-cli query tools --json` — outputs a JSON array of tool
   entries from two sources:
   - **Compiled-in** (harness-cli commands, `source: "compiled"`)
   - **User-registered** (from `tool` table, `source: "registered"`)
3. New command `harness-cli query tools --summary` — compact one-liner list for
   agent context (avoids dumping full JSON into the model).
4. New command `harness-cli query tools --responsibility <name>` — filtered view.
5. New command `harness-cli tool register` — registers external tools with
   validation.
6. New command `harness-cli tool remove` — deregisters a tool.
7. New schema: `tool` table for user-registered tools.
8. Update `HARNESS_COMPONENTS.md` — Tool access: Partial → Covered; Tool
   descriptions: Partial → Covered.

**Tool entry schema (JSON output):**

```json
{
  "provider": "harness-cli | custom",
  "command": "story verify",
  "description": "Run a story's verify_command and record pass/fail",
  "args": [
    { "name": "id", "type": "string", "required": true, "help": "Story id" }
  ],
  "responsibility": "Verification",
  "source": "compiled | registered",
  "since": "0.1.6"
}
```

**Registration validation rules:**

| Check | Enforcement |
|-------|-------------|
| `--name` is unique | Reject duplicate names; show existing entry on error |
| `--command` path exists or is on PATH | Warn if not found; require `--force` to register anyway |
| `--description` is 10-200 chars | Reject too short or too long |
| `--responsibility` is a valid Runtime Substrate responsibility | Reject unknown values; print accepted list on error |
| `--args` follow `name:type:required` schema | Parse and reject malformed arg specs |

**Registration example:**

```bash
harness-cli tool register \
  --name "deploy-check" \
  --command "./scripts/deploy-check.sh" \
  --description "Verify staging env is healthy before production deploy" \
  --responsibility Verification \
  --args "env:enum:required:staging,production"
```

**Acceptance Criteria:**

| # | Criterion | How to verify |
|---|-----------|---------------|
| 1 | `docs/TOOL_REGISTRY.md` lists every CLI command with arguments and purpose. | Read the file. Every command visible in `harness-cli --help` is documented. |
| 2 | `harness-cli query tools --json` returns valid JSON listing all compiled-in and registered commands. | Run command, pipe to `jq .`; verify each entry has `command`, `description`, `args`, `responsibility`. |
| 3 | `harness-cli query tools --summary` prints a compact one-liner list. | Run command. Output is a table with command, responsibility, and short description. |
| 4 | `harness-cli query tools --responsibility Verification` filters correctly. | Run command. Only verification-related tools appear. |
| 5 | `harness-cli tool register` validates inputs and stores in `tool` table. | Register a tool with valid inputs. Query `tool` table. Row exists. |
| 6 | `harness-cli tool register` rejects invalid inputs (missing description, bad responsibility, duplicate name). | Attempt invalid registrations. All rejected with actionable errors. |
| 7 | `harness-cli tool remove --name <name>` deregisters a tool. | Register then remove. Query `tool` table. Row gone. |
| 8 | A test asserts every harness-cli subcommand has a compiled-in registry entry. | Run `cargo test`. |
| 9 | `cargo test` passes. | Run `cargo test`. |

**Lane:** Normal (new query subcommand + schema + documentation, touches all four
layers).

---

### US-020: Batch Story Verification

**Background:**

`story verify <id>` verifies one story at a time. There is no way to verify all
stories with `verify_command` set in a single pass. PHASE4.md deferred "batch
verification across all stories" to Phase 5.

**Reason:**

Runtime Substrate (arXiv:2605.13357) says H4 requires consistent proof checks. A
single-story command requires agents to enumerate stories manually. Batch
verification lets an agent or CI pipeline confirm all story contracts in one
command.

**Use cases:**

1. **Pre-merge confidence gate:** Run `story verify-all` before merging to confirm
   nothing regressed. Like `cargo test` but for story-level contracts.
2. **Benchmark validation:** `harness-benchmark` calls `story verify-all` on the
   target repo to check that stories still pass after agent work.
3. **After refactoring:** Unit tests pass, but did you break any story-level
   behavior? `verify-all` confirms product contracts still hold.

**Solution:**

1. New command `harness-cli story verify-all` — queries all stories with non-null
   `verify_command`, runs each, prints per-story results, and exits with code 1 if
   any fail.
2. Summary output:
   `N stories verified: X passed, Y failed, Z skipped (no verify_command)`.
3. Update `docs/HARNESS.md` with batch verification workflow.
4. Update `docs/HARNESS_MATURITY.md` — H4 current status: Partial → Achieved.

**Acceptance Criteria:**

| # | Criterion | How to verify |
|---|-----------|---------------|
| 1 | `harness-cli story verify-all` runs all stories with `verify_command` and prints summary. | Add 3 stories (2 with verify commands, 1 without). Run `verify-all`. Output shows 2 verified, 1 skipped. |
| 2 | Exit code is 0 when all pass, 1 when any fail. | Add a story with `--verify "exit 1"`. Run `verify-all`. Exit code is 1. |
| 3 | Each story result is printed individually before the summary. | Output includes per-story lines: `Story US-XXX: pass/fail`. |
| 4 | `docs/HARNESS_MATURITY.md` H4 current status is updated to "Achieved." | Read the file. |
| 5 | `cargo test` passes with tests covering pass-all, fail-some, and no-verify-command cases. | Run `cargo test`. |

**Lane:** Normal (new CLI subcommand, touches all four code layers + documentation).

---

### US-021: Intervention Recording Schema

**Background:**

`HARNESS_COMPONENTS.md` notes: "Human interventions are not separated from normal
agent actions, and there is no review-event schema." Traces record what happened,
but don't distinguish agent-autonomous actions from human-directed corrections.

**Reason:**

"The Last Harness" (arXiv:2604.21003) describes the Evolution role as learning from
where humans intervene. Without structured intervention records, the harness can't
identify which agent behaviors need improvement. The improvement proposal pipeline
(US-024) needs this data to propose targeted fixes.

**Solution:**

1. New migration `scripts/schema/003-intervention.sql`:
   ```sql
   CREATE TABLE intervention (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     created_at TEXT NOT NULL DEFAULT (datetime('now')),
     trace_id INTEGER REFERENCES trace(id),
     story_id TEXT,
     type TEXT NOT NULL CHECK(type IN ('correction','override','escalation','approval')),
     description TEXT NOT NULL,
     source TEXT NOT NULL CHECK(source IN ('human','reviewer','ci','agent')),
     impact TEXT
   );
   ```
2. New command `harness-cli intervention add --trace <id> --type <type>
   --description <text> --source <source>`.
3. New query `harness-cli query interventions` — lists interventions with optional
   `--trace`, `--story`, and `--type` filters.
4. Update trace recording prompt — after recording a trace, print a reminder:
   `Reminder: Record any human corrections with: harness-cli intervention add`.
5. Update `HARNESS_COMPONENTS.md` — Intervention recording: Partial → Covered.
6. Update `docs/HARNESS.md` — add intervention recording to the Harness Delta
   section.

**Intervention types:**

| Type | Meaning | Example |
|------|---------|---------|
| `correction` | Human fixed something the agent got wrong | "Use error handling, not unwrap()" |
| `override` | Human rejected agent's approach entirely | "Don't add a new table, use existing backlog table" |
| `escalation` | Risk or scope was raised by human | "This is high-risk, add a decision record" |
| `approval` | Human explicitly approved a risky action | "Yes, proceed with schema migration" |

**Sources:**

| Source | Who triggered it |
|--------|-----------------|
| `human` | Direct human feedback (PR review, chat, verbal) |
| `reviewer` | Code review tool or automated review bot |
| `ci` | CI/CD pipeline caught an issue |
| `agent` | Another agent flagged the issue (future: sub-agents) |

**Recording triggers (how agents know to record):**

1. Pre-close gate prompts it — trace recording prints a reminder.
2. Agent instructions in `HARNESS.md` document the policy.
3. Humans can record directly after giving feedback.
4. Imperfect capture is acceptable for Phase 5 — partial data still feeds US-024.

**Acceptance Criteria:**

| # | Criterion | How to verify |
|---|-----------|---------------|
| 1 | `scripts/schema/003-intervention.sql` creates the `intervention` table with the specified columns and constraints. | Read the file. |
| 2 | `harness-cli migrate` applies migration 003 on an existing v2 database. | Run `init`, `migrate`. Verify `schema_version` contains version 3. |
| 3 | `harness-cli intervention add` stores a record and prints confirmation. | Run command, query `intervention` table. |
| 4 | `harness-cli query interventions` returns stored records. | Add 2 interventions, query. Both appear. |
| 5 | `--trace`, `--story`, and `--type` filters work. | Add interventions with different traces/stories/types. Filters return correct subsets. |
| 6 | Trace recording prints intervention reminder after confirmation. | Record a trace. Output includes the reminder line. |
| 7 | `cargo test` passes. | Run `cargo test`. |

**Lane:** Normal (schema migration + new CLI commands across all four layers).

---

### US-022: Context Rule Measurement

**Background:**

`CONTEXT_RULES.md` defines what agents should read per phase and lane, but there's
no measurement of whether agents actually follow these rules. PHASE4.md deferred
"context rule enforcement / measurement" to Phase 5.

**Reason:**

NLAHs (arXiv:2603.25723) says NL policies need measurement before enforcement. You
can't enforce what you can't measure. The `files_read` field in traces already
captures what agents read — US-022 adds a command that compares that against what
`CONTEXT_RULES.md` says they *should* have read.

**The feedback loop:**

```
score-context → "you read 3/5 Must docs, missed: ARCHITECTURE.md"
  → agent reads the missing docs next time → score goes up
  → if agents consistently miss the same doc → propose command (US-024) suggests
    updating context rules
```

**Solution:**

1. New command `harness-cli score-context <trace-id>` — reads the trace's
   `files_read`, determines lane from linked intake, infers phase from trace
   content, and compares against `CONTEXT_RULES.md` rules compiled into the binary.
2. Output: Must-read compliance (X/Y), Should-read compliance, over-reading
   advisory.
3. Advisory output — no exit code change, similar to `score-trace`.
4. Phase inference heuristic:
   - Has `story_id` + `files_changed` → implementation/validation phase.
   - Has only `intake_id`, no `files_changed` → intake/planning phase.
   - Has `outcome = completed` → trace phase.
5. "Relevant" doc matching uses Retrieval Triggers from `CONTEXT_RULES.md`:
   - If `files_changed` includes `scripts/schema/*` → flag decision 0004 as Must.
   - If `files_changed` includes CLI code → flag decision 0005 as Must.
   - Pattern paths (`docs/stories/*`) match if any file under that path was read.

**Example output:**

```
harness-cli score-context 43
→ Trace #43 | Lane: normal | Phase: implementation
→
→ Must-read compliance: 4/5
→   ✓ Files being changed
→   ✓ Adjacent files with same pattern
→   ✓ Relevant product docs
→   ✓ Relevant story packet
→   ✗ MISSING: docs/ARCHITECTURE.md (Must for structural changes)
→
→ Should-read: 2/3
→ Over-reading: 1 doc (docs/HARNESS_MATURITY.md — Skip for normal implementation)
→
→ Context score: 4/5 must, 2/3 should
```

**Acceptance Criteria:**

| # | Criterion | How to verify |
|---|-----------|---------------|
| 1 | `harness-cli score-context <trace-id>` prints required vs actual docs read. | Record a trace with `--files-read` including some required docs. Run `score-context`. Output shows which required docs were read and which were missed. |
| 2 | Lane is inferred from the trace's linked intake. | Link trace to a `normal` lane intake. Score shows normal-lane requirements. |
| 3 | Missing required docs are listed with their Must/Should priority. | Output distinguishes Must-read misses from Should-read misses. |
| 4 | Over-reading (docs marked Skip that were read) is flagged as advisory. | Read a doc marked Skip for the lane. Score notes it. |
| 5 | Retrieval Triggers are applied (e.g., schema changes flag decision 0004). | Create trace with `files_changed` including a schema file. Score flags decision 0004 as Must. |
| 6 | `cargo test` passes with tests covering all lanes. | Run `cargo test`. |

**Lane:** Normal (new CLI command, requires compiled-in context rule lookup table).

---

### US-023: Drift Detection / Entropy Score

**Background:**

`HARNESS_COMPONENTS.md` notes: "No drift detector, stale-doc audit, or entropy
score exists." PHASE4.md deferred this to Phase 5.

**Reason:**

Continual Harness (arXiv:2605.09998) says self-improvement requires knowing what's
stale. Before the harness can propose improvements (US-024), it needs to identify
what has drifted: stories with no recent traces, decisions never verified, docs not
referenced in any trace, and backlog items that predicted impact but have no
outcome.

**Solution:**

1. New command `harness-cli audit` — scans durable records and reports six drift
   categories:
   - **Orphaned stories:** `status = 'accepted'` but no linked trace.
   - **Unverified stories:** `verify_command` set but `last_verified_result` is null.
   - **Unverified decisions:** `verify_command` set but `last_verified_result` is null.
   - **Open backlog without outcomes:** `predicted_impact` set but `actual_outcome`
     is null and `status = 'implemented'`.
   - **Stale stories:** most recent linked trace >30 days old, status not
     `implemented`.
   - **Broken tools:** registered tools whose `command` path does not exist on
     disk.
2. Output: per-category counts, specific record IDs, and an overall entropy score
   (0-100, lower is better).
3. New `docs/HARNESS_AUDIT.md` documenting what the audit checks and how to
   interpret scores.

**Entropy score calculation:**

```
score = (orphaned_stories × 10)
      + (unverified_stories × 5)
      + (unverified_decisions × 5)
      + (open_backlog_no_outcome × 2)
      + (stale_stories × 3)
      + (broken_tools × 8)

capped at 100
```

| Range | Interpretation |
|-------|---------------|
| 0 | Perfect — everything verified, traced, outcomes recorded, tools healthy |
| 1-25 | Healthy — minor housekeeping needed |
| 26-50 | Attention needed — drift is accumulating |
| 51-100 | Action required — significant staleness undermining harness value |

**Example output:**

```
harness-cli audit
→ === Harness Drift Audit ===
→
→ Orphaned stories (accepted, no traces): 2
→   - US-042: "Add retry logic" (accepted 45 days ago)
→   - US-043: "Improve error messages" (accepted 30 days ago)
→
→ Unverified stories: 1
→   - US-019: has verify_command, never verified
→
→ Unverified decisions: 0
→
→ Open backlog without outcomes: 3
→   - #4: "Reduce trace verbosity"
→   - #7: "Add lint step"
→   - #9: "Update context rules"
→
→ Stale stories: 1
→   - US-015: last trace 40 days ago, status still 'in_progress'
→
→ Broken tools: 0
→
→ Entropy score: 34/100 (lower is better)
→   Breakdown: orphaned=20, unverified=5, no-outcomes=6, stale=3, broken=0
```

**Acceptance Criteria:**

| # | Criterion | How to verify |
|---|-----------|---------------|
| 1 | `harness-cli audit` prints category counts and specific record IDs for each drift category. | Create stories, decisions, and backlog items in various states. Run `audit`. Verify correct categorization. |
| 2 | Entropy score is 0 when all records are clean. | Create a clean dataset (all verified, traced, outcomes recorded). Score is 0. |
| 3 | Entropy score increases proportionally with drift. | Add unverified stories and open backlog items. Score increases. |
| 4 | Broken tools check finds registered tools with missing command paths. | Register a tool with a nonexistent path. Run `audit`. Broken tools category lists it. |
| 5 | `docs/HARNESS_AUDIT.md` documents each check and score interpretation. | Read the file. |
| 6 | `cargo test` passes with tests covering clean, partial, and high-drift states. | Run `cargo test`. |

**Lane:** Normal (new CLI command + documentation, queries existing tables plus
`tool` table from US-019, no schema change beyond US-019).

---

### US-024: Improvement Proposal Pipeline

**Background:**

H5 requires: "Repeated friction patterns are summarized into proposed harness
changes." The backlog outcome loop (US-011) captures predicted vs actual impact.
The audit command (US-023) identifies drift. The friction query (US-009) shows
friction with context. The intervention table (US-021) records human corrections.
But no command composes these into actionable improvement proposals.

**Reason:**

"The Last Harness" (arXiv:2604.21003) says the Evolution role must be mechanical.
Runtime Substrate (arXiv:2605.13357) defines H5 as "the harness can propose safe
improvements." This is the capstone story for Phase 5.

**Solution:**

1. New command `harness-cli propose` — analyzes friction entries, audit results,
   intervention patterns, and backlog outcomes to generate structured improvement
   proposals.
2. Each proposal includes: title, harness component affected, evidence, predicted
   impact, risk level, suggested action, and validation plan.
3. Proposals are printed as structured text and optionally stored as `proposed`
   backlog items via `--commit` flag.
4. Update `docs/HARNESS_MATURITY.md` — H5 current status: Not achieved → Partial.
5. New `docs/IMPROVEMENT_PROTOCOL.md` documenting the proposal review workflow.

**Pipeline architecture:**

```
┌─────────────┐   ┌──────────────────┐   ┌─────────────────┐
│  Friction   │   │  Interventions   │   │  Audit/Drift    │
│  (existing) │   │  (US-021)        │   │  (US-023)       │
└──────┬──────┘   └────────┬─────────┘   └────────┬────────┘
       │                   │                       │
       └───────────────────┼───────────────────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Pattern Detection    │
               │  (group, count, rank) │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Proposal Generation  │
               │  (structured output)  │
               └───────────┬───────────┘
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
              Print only    --commit
              (advisory)    (creates backlog items)
```

**Pattern detection (rule-based, not LLM):**

- Friction: group by text similarity, flag patterns with ≥2 occurrences.
- Interventions: group by type + description, flag patterns with ≥2 occurrences.
- Audit: each non-zero drift category generates a housekeeping proposal.

**Confidence scoring:**

| Confidence | Criteria |
|-----------|----------|
| High | Pattern seen ≥3 times + affects a documented component + clear action |
| Medium | Pattern seen 2 times, or ≥3 times but action is ambiguous |
| Low | Single occurrence from audit drift, or pattern too vague for specific action |

**Example output:**

```
harness-cli propose
→ === Improvement Proposals ===
→
→ Proposal 1 (high confidence):
→   Title: Add error handling guidance to CONTEXT_RULES.md
→   Component: Context selection
→   Evidence: 3 interventions (type=correction) about error handling
→   Predicted impact: Fewer correction interventions for error handling
→   Risk: Tiny
→   Suggested action: Add retrieval trigger for Rust error paths
→   Validation: Next 5 tasks show fewer error handling corrections
→
→ Proposal 2 (medium confidence):
→   Title: Reclassify schema changes as normal-lane
→   Component: Task specification
→   Evidence: 3 escalations (tiny→normal) when tasks touched schema
→   Predicted impact: Fewer mid-task escalations
→   Risk: Normal
→   Suggested action: Update FEATURE_INTAKE.md default lane for schema
→   Validation: Next schema task starts as normal without escalation
→
→ 2 proposals generated. Use --commit to create backlog items.
```

**`--commit` behavior:**

```bash
harness-cli propose --commit
→ Created backlog item #12: "Add error handling guidance"
→   predicted_impact: "Fewer correction interventions"
→   status: proposed
```

Items appear in `query backlog --open` for human review.

**Acceptance Criteria:**

| # | Criterion | How to verify |
|---|-----------|---------------|
| 1 | `harness-cli propose` analyzes friction, audit, and intervention data and prints at least one proposal when patterns exist. | Create friction entries and interventions with repeated patterns. Run `propose`. Output includes structured proposals. |
| 2 | Each proposal has title, component, evidence, predicted impact, risk, suggested action, and validation plan. | Read output. All fields present. |
| 3 | Confidence levels are assigned based on pattern frequency. | Create patterns with 2 and ≥3 occurrences. Medium and high confidence respectively. |
| 4 | `harness-cli propose --commit` creates `proposed` backlog items. | Run with `--commit`. Query backlog. New items exist with status `proposed` and `predicted_impact` filled. |
| 5 | `docs/IMPROVEMENT_PROTOCOL.md` documents the proposal-to-implementation workflow. | Read the file. |
| 6 | `docs/HARNESS_MATURITY.md` H5 updated to "Partial." | Read the file. |
| 7 | `cargo test` passes. | Run `cargo test`. |

**Lane:** High-risk (new analysis logic, changes harness evolution model, affects
maturity claims, requires decision record).

---

## Out of Scope for Phase 5

| Item | Why deferred | Phase |
|------|-------------|-------|
| Tool usage analytics | Unreliable without proper instrumentation — string-matching traces is fragile | Phase 6 (with explicit `tool run` wrapper or `--tools-used` flag) |
| Executable agent skills (NexAU "Skills") | Platform-dependent, requires skill registry standard | Phase 6 |
| Story dependency graph | Schema change + dependency resolution is complex | Phase 5.5 |
| Trace replay / comparison | Needs more trace data to be useful | Phase 5.5 |
| Sub-agents | No use case yet in this repo | Phase 6+ |
| Config parameter search (Harbor) | Needs more benchmark runs | Phase 6+ |
| Enforced permission layer | Needs measurement data from US-022 first | Phase 6 |
| Runtime middleware | Framework-dependent, no application code exists | Phase 6+ |
| Export/import of harness state | Nice-to-have, not on the H4→H5 critical path | Phase 6 |
| Benchmark comparison attribution (US-014) | Lives in `harness-benchmark` | Benchmark work |
| Installer propagation of Phase 3/4/5 docs | Separate PR, not core harness work | Separate |

---

## Implementation Sequence

```
Step 1: US-019 — Tool registry
  - Create scripts/schema/003-tool-registry.sql (tool table)
  - Add ToolAction to interface.rs (register, remove)
  - Add QueryAction::Tools to interface.rs (--json, --summary, --responsibility)
  - Add compiled-in registry Vec<ToolEntry> to domain.rs
  - Add tool CRUD and query to infrastructure.rs
  - Write docs/TOOL_REGISTRY.md
  - Update HARNESS_COMPONENTS.md
  - Test: registration validation, query output, compiled-in completeness
  Estimated effort: ~4-5 hours

Step 2: US-020 — Batch story verification
  - Add StoryAction::VerifyAll to interface.rs
  - Add verify_all_stories to application.rs / infrastructure.rs
  - Update HARNESS.md and HARNESS_MATURITY.md
  - Test: pass-all, fail-some, no-verify-command
  Estimated effort: ~2-3 hours

Step 3: US-021 — Intervention recording
  - Create scripts/schema/004-intervention.sql
  - Add InterventionAction to interface.rs
  - Add intervention commands to all four layers
  - Update trace recording to print reminder
  - Update HARNESS_COMPONENTS.md and HARNESS.md
  - Test: add, query, filters
  Estimated effort: ~4-5 hours

Step 4: US-022 — Context rule measurement
  - Compile context rules into a lookup table in domain.rs
  - Add score-context command to interface.rs
  - Add context scoring logic to application.rs
  - Add retrieval trigger matching
  - Test: all lanes, phase inference, retrieval triggers
  Estimated effort: ~4-5 hours

Step 5: US-023 — Drift detection / entropy score
  - Add `audit` command querying existing tables + tool table
  - Write docs/HARNESS_AUDIT.md
  - Test: clean, partial, and high-drift states; broken tools
  Estimated effort: ~3-4 hours

Step 6: US-024 — Improvement proposal pipeline
  - Add `propose` command composing friction + audit + interventions
  - Add pattern detection logic (grouping, counting, ranking)
  - Add --commit flag to create backlog items
  - Write docs/IMPROVEMENT_PROTOCOL.md
  - Write docs/decisions/0007-improvement-proposal-rules.md
  - Update HARNESS_MATURITY.md
  - Test: pattern detection, confidence levels, commit behavior
  Estimated effort: ~5-6 hours

Step 7: Cross-references and documentation
  - Update GLOSSARY.md with new terms (tool registry, intervention,
    entropy score, improvement proposal, context score)
  - Update HARNESS_COMPONENTS.md coverage assessment
  - Update HARNESS_MATURITY.md current assessment table
  - Record Phase 5 trace
  Estimated effort: ~1-2 hours
```

**Total estimated effort:** ~23-30 hours

---

## Execution Workflow

1. **Branch:** `git checkout -b feature/phase-5-evolution-infrastructure main`
2. **Implement US-019 → US-020 → US-021 → US-022 → US-023 → US-024** (in order)
3. **Update cross-references** (HARNESS.md, HARNESS_COMPONENTS.md,
   HARNESS_MATURITY.md, GLOSSARY.md)
4. **Run `cargo test`** — all tests must pass
5. **Run `cargo clippy`** — no warnings
6. **Run benchmark** in `harness-benchmark`
7. **Compare:** benchmark results against Phase 4 baseline
8. **Merge:** Only when benchmark shows stable or improved results

---

## Expected Benchmark Deltas

| Metric | Phase 4 (current) | Phase 5 Target | Reasoning |
|--------|-------------------|----------------|-----------|
| Functional score | 37/37 (100%) | 37/37 (100%) | Phase 5 doesn't change app code |
| Harness compliance | 31/31 (100%) | 31/31 (100%) | Already perfect |
| Trace quality | 2.5-2.8/3.0 | 2.8-3.0/3.0 | Context scoring + audit give agents better feedback |
| Lane accuracy | 6/6 | 6/6 | Already perfect |
| Wall time | ~1800-1900s | ~2000-2100s | Slight increase from audit and context scoring |
| Token cost | ~$22-23 | ~$23-25 | Slight increase from reading audit output |

---

## What Would Signal Success

1. `cargo test` passes with coverage for all six stories.
2. `story verify-all` confirms all stories in one pass — H4 fully achieved.
3. `audit` identifies real drift in benchmark runs.
4. `propose` generates at least one actionable proposal from friction data.
5. Context scoring shows whether agents follow `CONTEXT_RULES.md`.
6. Benchmark trace quality rises to ≥2.8/3.0.
7. No regression in functional score, harness compliance, or lane accuracy.

## What Would Signal Failure

- Batch verification disagrees with individual `story verify` results.
- Audit command produces false positives that confuse agents.
- Proposal pipeline generates low-quality or circular proposals.
- Context rule measurement penalizes useful over-reading.
- Tool registration validation is too strict, discouraging adoption.
- `cargo test` or `cargo clippy` failures.
- Functional score drops (overhead confused the agent).

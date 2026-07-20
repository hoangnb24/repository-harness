# Harness Maturity Ladder

> **Compatibility reference — not a current product maturity claim.** H0-H5
> describes the historical control-plane program. The default workflow now
> evaluates concrete repository legibility, executable constraints, observable
> validation, and human attention rather than advancement through this ladder.

This ladder defines how `repository-harness` should progress from static
agent instructions to measurable harness improvement.

The levels are intentionally verifiable. A level is achieved only when its
criteria can be inspected in repository files, durable Harness records, or
benchmark output.

## Levels

### H0 - Bare Environment

The model operates with no repository harness. It receives a prompt and may
produce a patch, but the repo does not tell it how to classify, validate, or
record work.

Criteria:

- No `AGENTS.md` Harness block exists.
- No feature intake policy exists.
- No story, decision, validation, or trace artifact exists.

Required files:

- None.

Benchmark indicators:

- Functional score is the only meaningful metric.
- Harness compliance: 0%.
- Trace quality: 0/3.

Current status:

- Passed. This repository is beyond H0.

Activated responsibilities:

- None.

### H1 - Scaffolding And Policy

The repository contains static operating instructions, templates, risk lanes,
and source-of-truth rules. Agents can follow a documented workflow, but durable
state may still be manual or incomplete.

Criteria:

- `AGENTS.md` points agents to the Harness operating docs.
- `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, and `docs/ARCHITECTURE.md`
  exist.
- Story, decision, and validation templates exist under `docs/templates/`.
- `docs/TEST_MATRIX.md` defines proof columns and status meanings.

Required files:

- `AGENTS.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/templates/story.md`
- `docs/templates/decision.md`
- `docs/templates/validation-report.md`

Benchmark indicators:

- Harness compliance: 20-40%.
- Lane accuracy improves when agents read the intake policy.
- Trace quality remains low unless traces are separately requested.

Current status:

- Achieved. H1 files exist and are used by current Harness instructions.

Activated responsibilities:

- Task specification.
- Permissions.
- Project memory.
- Verification.

### H2 - Durable State And Observability

The repository has structured operational records and explicit observation
rules. Agents can record what happened, connect work to stories, and write
traces with predictable depth.

Criteria:

- `scripts/bin/harness-cli` can record intake, story, decision, backlog, and trace
  data in `harness.db`.
- `scripts/schema/001-init.sql` defines durable tables for intake, story,
  decision, backlog, and trace records.
- `docs/HARNESS_COMPONENTS.md` maps files and responsibilities.
- `docs/HARNESS_MATURITY.md` defines H0-H5 with measurable criteria.
- `docs/TRACE_SPEC.md` defines trace fields, quality tiers, and friction
  capture.
- `docs/CONTEXT_RULES.md` defines phase-by-lane context rules.
- `AGENTS.md` and `docs/HARNESS.md` reference the Phase 2 operating docs.

Required files:

- `scripts/bin/harness-cli`
- `scripts/schema/001-init.sql`
- `docs/HARNESS_COMPONENTS.md`
- `docs/HARNESS_MATURITY.md`
- `docs/TRACE_SPEC.md`
- `docs/CONTEXT_RULES.md`

Benchmark indicators:

- Harness compliance: 75-90%.
- Trace quality: at least 2.0/3 on normal-lane tasks.
- Lane accuracy: 6/6 on the current benchmark suite.
- Friction captured: at least 4/6 benchmark tasks when friction exists.

Current status:

- Achieved. Durable state exists, and the Phase 2 docs define the
  observability and context specification. Phase 3 active scoring builds on
  this layer.

Activated responsibilities:

- Task state.
- Observability.
- Failure attribution.
- Context selection.
- Entropy auditing.

### H3 - Active Observability And Evolution

The harness can evaluate its own operational data and turn repeated failures
into prioritized improvements.

Criteria:

- Trace quality can be scored by a repeatable command or benchmark step.
- Harness friction can be grouped by component from `docs/HARNESS_COMPONENTS.md`.
- Backlog items include predicted impact and actual outcome after completion.
- Benchmark comparison output identifies which harness responsibility moved or
  regressed.

Required files:

- H2 files.
- A benchmark protocol or report that references maturity levels.
- A documented trace quality scoring method.
- A documented friction-to-backlog review loop.

Benchmark indicators:

- Harness compliance: 85-95%.
- Trace quality: 2.3-2.7/3.
- Friction captured and classified by component for most failed or awkward
  tasks.
- Regressions include an attributed harness component.

Current status:

- Partially achieved by Phase 3. `scripts/bin/harness-cli score-trace` scores trace
  quality against tier rules, `query friction` includes linked intake context,
  the `trace` command now prints that score at write time, and the backlog
  outcome loop documents predicted impact versus actual outcome. Full H3 still
  requires benchmark comparison output that attributes moved or regressed
  responsibilities.

Activated responsibilities:

- Observability.
- Failure attribution.
- Entropy auditing.
- Intervention recording.

### H4 - Automated Verification

The harness can run or orchestrate proof checks consistently and can reject or
flag incomplete work before the final response.

Criteria:

- A documented verification command or protocol runs the expected checks for a
  selected story and lane.
- Stories can store and execute a `verify_command`.
- Trace recording warns when a linked story has a verification command that has
  not passed.
- Missing validation evidence is surfaced before a task is marked implemented.

Required files:

- H3 files.
- A verification protocol or command reference.
- Validation report examples tied to story proof columns.
- Story verification command documentation.

Benchmark indicators:

- Functional score remains stable.
- Harness compliance: at least 90%.
- Fewer false "done" claims in benchmark review.
- Missing proof is detected before merge or final response.

Current status:

- Achieved by Phase 5. `scripts/bin/harness-cli story verify <id>` runs
  story-level proof commands, records pass/fail state, `trace --story` warns
  before close when verification has not passed, and
  `scripts/bin/harness-cli story verify-all` runs all configured story proof
  commands in one pass. Proof-column automation remains a future enhancement,
  but H4's required automated verification gate is now present.

Activated responsibilities:

- Verification.
- Task state.
- Permissions.
- Intervention recording.

### H5 - Self-Improving Harness

The harness can use traces, benchmark results, and backlog outcomes to propose
or apply safe improvements to itself.

Criteria:

- Repeated friction patterns are summarized into proposed harness changes.
- Proposed changes include predicted impact, risk, validation plan, and rollback
  criteria.
- Completed changes compare predicted impact with actual benchmark or trace
  outcomes.
- High-risk harness changes pause for human confirmation before changing source
  hierarchy, architecture direction, or validation requirements.

Required files:

- H4 files.
- Self-improvement protocol.
- Historical improvement reports.
- Backlog outcome reviews.

Benchmark indicators:

- Harness compliance remains at least 90% across repeated benchmark runs.
- Trace quality remains at least 2.5/3.
- Improvements show measurable positive deltas or are explicitly reverted.
- Scope creep and validation weakening are caught by policy.

Current status:

- Partially achieved by Phase 5. `scripts/bin/harness-cli audit` detects
  durable-state drift, `scripts/bin/harness-cli propose` generates structured
  improvement proposals from friction, interventions, and audit results, and
  `docs/IMPROVEMENT_PROTOCOL.md` defines the review loop. H5 is not fully
  achieved until repeated benchmark outcomes prove proposed improvements create
  measurable positive deltas or are explicitly reverted.

Activated responsibilities:

- Entropy auditing.
- Failure attribution.
- Intervention recording.
- Permissions.

## Current Assessment

| Level | Status | Evidence |
| --- | --- | --- |
| H0 | Passed | Harness docs, templates, and durable records exist. |
| H1 | Achieved | `AGENTS.md`, `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, `docs/ARCHITECTURE.md`, `docs/templates/*`, and `docs/TEST_MATRIX.md` exist. |
| H2 | Achieved | `scripts/bin/harness-cli`, `scripts/schema/001-init.sql`, durable story records, `docs/HARNESS_COMPONENTS.md`, `docs/HARNESS_MATURITY.md`, `docs/TRACE_SPEC.md`, and `docs/CONTEXT_RULES.md` define the Phase 2 surface. |
| H3 | Partial | Phase 3 adds `scripts/bin/harness-cli score-trace`, enriched friction context, and the backlog outcome loop; Phase 4 auto-scores traces on write. Component-level benchmark attribution remains open. |
| H4 | Achieved | Phase 4 adds story-level `verify_command`, `story verify`, and trace-time verification warnings. Phase 5 adds `story verify-all` for batch story proof. |
| H5 | Partial | Phase 5 adds `audit`, `score-context`, `intervention add/query`, `propose`, `docs/HARNESS_AUDIT.md`, and `docs/IMPROVEMENT_PROTOCOL.md`; repeated benchmark outcome proof remains open. |

## Responsibility Activation

| Responsibility | H0 | H1 | H2 | H3 | H4 | H5 |
| --- | --- | --- | --- | --- | --- | --- |
| Task specification | Missing | Covered | Covered | Covered | Covered | Covered |
| Context selection | Missing | Partial | Covered | Covered | Covered | Covered |
| Tool access | Missing | Partial | Partial | Partial | Covered | Covered |
| Project memory | Missing | Covered | Covered | Covered | Covered | Covered |
| Task state | Missing | Partial | Covered | Covered | Covered | Covered |
| Observability | Missing | Missing | Partial | Covered | Covered | Covered |
| Failure attribution | Missing | Missing | Partial | Covered | Covered | Covered |
| Verification | Missing | Partial | Partial | Partial | Covered | Covered |
| Permissions | Missing | Partial | Partial | Partial | Covered | Covered |
| Entropy auditing | Missing | Missing | Partial | Covered | Covered | Covered |
| Intervention recording | Missing | Partial | Partial | Covered | Covered | Covered |

## Phase 3 Interpretation

Phase 3 starts the H2 to H3 transition. It claims active trace scoring and a
documented improvement feedback loop, but it does not claim full H3 because
benchmark comparison and component-level regression attribution are explicitly
outside this repository's Phase 3 scope.

## Phase 4 Interpretation

Phase 4 starts the H3 to H4 transition. It gives stories the same mechanical
verification pattern that decisions already had, records story verification
results in the durable layer, auto-scores traces when they are written, and
warns before close when a linked story's verification has not passed. It does
not claim full H4 because benchmark execution, batch verification, and automatic
proof-column updates remain separate work.

## Phase 5 Interpretation

Phase 5 completes H4 by adding batch story verification and starts H5 by adding
tool discovery, intervention records, context scoring, drift audit, and
deterministic proposal generation. The repository may claim H5 partial only
when those commands and docs are present and validated; it must not claim full
H5 until benchmark runs or trace outcomes prove the proposal loop improves the
harness over time.

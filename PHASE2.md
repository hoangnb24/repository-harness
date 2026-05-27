sk-dummse 2 Implementation Plan — Observability & Taxonomy

**Target repo:** `harness-experimental` (feature branch off `main`)
**Validation:** `harness-benchmark` re-run after implementation
**Current harness maturity:** ~H1.5 (structured state exists, traces can be recorded, but no observability, no taxonomy, no evolution loop)
**Target maturity:** H2 (component observability, structured traces, maturity ladder, context guidance)

---

## What Phase 2 Is

Phase 2 creates the **conceptual infrastructure** that all future phases depend on. It answers:

- "What components does this harness have?" (taxonomy)
- "What should agents record when they work?" (trace spec)
- "How do we measure if the harness is getting better?" (maturity ladder)
- "How does an agent decide what to read for a given task?" (context rules)

Phase 2 is **pure specification work**. No new code, no CLI changes, no schema migrations. Only markdown documents added to `docs/`.

---

## Why This Order Matters

```
US-003 Component Taxonomy
  ↓ defines what exists
US-005 Maturity Ladder
  ↓ defines where we're going
US-004 Trace Specification
  ↓ defines what to observe (uses taxonomy as structure)
US-006 Context Engineering Rules
  ↓ defines what info reaches the model (uses all of the above)
```

Each story builds on the previous. US-006 can't define context rules without knowing what components exist (US-003), what maturity level we're targeting (US-005), and what structured data the trace will produce (US-004).

---

## Stories

### US-003: Component Taxonomy

**Purpose:** Map every file and capability in `harness-experimental` to a recognized framework so we can evaluate coverage, attribute failures, and do ablation studies.

**What gets created:** `docs/HARNESS_COMPONENTS.md`

**Methodology:**
1. Inventory all harness files (AGENTS.md, docs/*, scripts/*, crates/*, templates/*)
2. Map each to the **11-responsibility framework** from Runtime Substrate (2605.13357):
   - Task specification, Context selection, Tool access, Project memory, Task state, Observability, Failure attribution, Verification, Permissions, Entropy auditing, Intervention recording
3. Also cross-reference with **NexAU 7-component decomposition** from AHE (2604.25850):
   - System prompts, Tool descriptions, Tool implementations, Middleware, Skills, Sub-agents, Long-term memory
4. Classify each responsibility as: **covered**, **partial**, or **missing**
5. For each "partial" or "missing": note what would move it to "covered"

**Output format:**

```markdown
# Harness Components

## Responsibility Map

| # | Responsibility | Status | Harness Files | Gap |
|---|----------------|--------|---------------|-----|
| 1 | Task specification | Covered | FEATURE_INTAKE.md, intake table | — |
| 2 | Context selection | Partial | AGENTS.md reading list | No dynamic rules |
| ... | ... | ... | ... | ... |

## NexAU Cross-Reference

| Component | Harness Equivalent | Notes |
|-----------|-------------------|-------|
| System prompts | AGENTS.md | Static, not task-type-aware |
| ... | ... | ... |

## Coverage Summary
- Covered: X/11
- Partial: Y/11
- Missing: Z/11
```

**Acceptance criteria:**
- Every file in the repo is mapped to at least one responsibility
- Every responsibility has a coverage status with evidence
- Gap column identifies what's needed (feeds US-004, US-005, US-006)
- NexAU cross-reference is complete

**Lane:** Normal

**Benchmark impact:**
- Should NOT change any benchmark scores directly (this is inventory, not behavior)
- Enables accurate measurement of subsequent stories

---

### US-005: Maturity Ladder

**Purpose:** Define H0–H5 with verifiable criteria specific to this project, so "improvement" has direction and progress is measurable.

**What gets created:** `docs/HARNESS_MATURITY.md`

**Methodology:**
1. Start from Runtime Substrate's H0–H3 ladder
2. Extend to H4–H5 for automation and self-improvement phases
3. For each level, define:
   - **Name and description** — what this level provides
   - **Verifiable criteria** — concrete, checkable conditions (not vague aspirations)
   - **Harness files that must exist** — specific deliverables
   - **Benchmark indicators** — which benchmark metrics should move at this level
   - **Current status** — where we are today
4. Cross-reference with the component taxonomy (US-003) to show which responsibilities activate at each level

**Output format:**

```markdown
# Harness Maturity Ladder

## Levels

### H0 — Bare Environment
The model operates with no harness. Produces only a patch.
- Criteria: No AGENTS.md, no intake, no trace
- Benchmark: Functional only, 0% harness compliance

### H1 — Scaffolding + Policy
Static structure, templates, risk lanes, reading order.
- Criteria: AGENTS.md exists, FEATURE_INTAKE.md exists, templates exist
- Benchmark: 0-30% harness compliance (agent may or may not follow)
- Status: ACHIEVED

### H2 — Durable State + Observability
Structured records, trace spec, component taxonomy, maturity tracking.
- Criteria: [specific file list and DB requirements]
- Benchmark: 60-80% harness compliance, trace quality ≥ 2.0
- Status: IN PROGRESS (Phase 2)

### H3 — Active Observability + Evolution
...

### H4 — Automated Verification
...

### H5 — Self-Improving Harness
...

## Current Assessment
| Level | Status | Evidence |
|-------|--------|----------|
| H0 | Passed | — |
| H1 | Achieved | [list of files] |
| H2 | In progress | [what's done, what's missing] |
```

**Acceptance criteria:**
- At least 5 levels defined (H0–H4 minimum)
- Each level has ≥3 verifiable criteria (not vague descriptions)
- Current level is assessed with evidence
- Benchmark indicators are specific (e.g., "harness compliance ≥ 60%")
- Cross-references US-003 component taxonomy

**Lane:** Normal

**Benchmark impact:**
- Should NOT change benchmark scores directly
- Provides the framework for interpreting all future benchmark comparisons
- PROTOCOL.md "Expected Results Per Phase" table should reference maturity levels

---

### US-004: Trace Specification

**Purpose:** Define what agents should actually record in the `trace` table, at what depth, in what structure. The `trace` table exists but is a bucket — this spec defines what goes in it.

**What gets created:** `docs/TRACE_SPEC.md`

**Methodology:**
1. Audit current `trace` table schema (001-init.sql lines 109-129):
   - `task_summary`, `actions_taken`, `files_read`, `files_changed`, `decisions_made`, `errors`, `outcome`, `duration_seconds`, `token_estimate`, `harness_friction`
2. For each field, define:
   - **Required vs optional** (currently everything is optional except `task_summary`)
   - **Format specification** (JSON arrays? free text? structured objects?)
   - **Minimum depth for each quality tier** (minimal/standard/detailed)
   - **Examples** of good vs bad traces
3. Define quality tiers that map to benchmark's trace quality scoring:
   - **Minimal (1):** Only `task_summary` filled
   - **Standard (2):** `task_summary` + `actions_taken` + `files_changed` + at least one of `errors`/`harness_friction`
   - **Detailed (3):** All fields populated with structured content
4. Add guidance per risk lane:
   - **Tiny:** Minimal trace is acceptable
   - **Normal:** Standard trace expected
   - **High-risk:** Detailed trace required
5. Define the **friction capture protocol**: when and how to populate `harness_friction`

**Output format:**

```markdown
# Trace Specification

## Field Reference

| Field | Type | Required | Format | Example |
|-------|------|----------|--------|---------|
| task_summary | TEXT | Yes | Free text, ≥10 chars | "Implemented CRUD bookmarks with validation" |
| actions_taken | TEXT | Standard+ | JSON array of strings | ["read PRODUCT_SPEC.md", "created src/routes/bookmarks.ts", ...] |
| files_changed | TEXT | Standard+ | JSON array of paths | ["src/routes/bookmarks.ts", "src/db.ts"] |
| ...

## Quality Tiers

### Minimal (score: 1)
- task_summary is filled (≥10 characters)
- Acceptable for: tiny lane tasks

### Standard (score: 2)
- task_summary + actions_taken + files_changed
- At least one of: errors, harness_friction
- Required for: normal lane tasks

### Detailed (score: 3)
- All fields populated with structured content
- Required for: high_risk lane tasks

## Friction Capture Protocol
...

## Examples
### Good trace (detailed)
### Adequate trace (standard)
### Insufficient trace (minimal for a normal-lane task)
```

**Acceptance criteria:**
- Every `trace` table column has a format spec and example
- Quality tiers are defined with minimum field requirements
- Lane-to-tier mapping is explicit
- At least 2 examples (good and bad)
- Friction capture protocol is documented
- Spec is referenced from HARNESS.md (update the "Task Loop" section)

**Lane:** Normal

**Benchmark impact — the primary Phase 2 mover:**
- **Trace quality:** 1.5 → 2.0+ (agents have clear guidance on what to write)
- **Friction captured:** Should improve (protocol tells agents when to record friction)
- **Harness compliance:** Indirect improvement (clearer expectations → more complete traces)

---

### US-006: Context Engineering Rules

**Purpose:** Define dynamic guidance for what information should reach the model, per risk lane and task phase. The current static reading list in AGENTS.md doesn't scale.

**What gets created:** `docs/CONTEXT_RULES.md` + update to `AGENTS.md` harness section

**Methodology:**
1. Define the **context phases** of a task:
   - **Intake phase:** What to read to classify the request
   - **Planning phase:** What to read to design the approach
   - **Implementation phase:** What to read while coding
   - **Validation phase:** What to read to verify correctness
   - **Trace phase:** What to read to write a good trace
2. For each phase × lane combination, specify:
   - **Must read** (always)
   - **Should read** (if relevant to the task)
   - **Skip** (not relevant at this phase)
3. Add token-budget awareness:
   - Tiny: Minimal context (~2K tokens of harness docs)
   - Normal: Standard context (~5K tokens)
   - High-risk: Full context (~10K tokens, including templates and prior decisions)
4. Define **retrieval triggers**: when should an agent go read something it hasn't read yet?
   - "If you're about to change a database schema, read `docs/decisions/` for prior schema decisions"
   - "If the task touches auth, read the high-risk story template"
5. Update AGENTS.md to reference CONTEXT_RULES.md instead of / in addition to the static reading list

**Output format:**

```markdown
# Context Engineering Rules

## Context Phases

### Intake Phase
Read to classify the request and choose a lane.

| Document | Tiny | Normal | High-Risk |
|----------|------|--------|-----------|
| FEATURE_INTAKE.md | Must | Must | Must |
| ARCHITECTURE.md | Skip | Should | Must |
| Prior decisions | Skip | Skip | Must |
| ...

### Planning Phase
...

### Implementation Phase
...

## Retrieval Triggers

| Trigger Condition | Action |
|-------------------|--------|
| Task touches database schema | Read docs/decisions/ for prior schema decisions |
| Task touches auth/authorization | Read high-risk-story templates |
| Task changes API shape | Read docs/product/api.md |
| ...

## Token Budget Guidance

| Lane | Target Context Budget | Reasoning |
|------|----------------------|-----------|
| Tiny | ~2K tokens | Only intake classification docs |
| Normal | ~5K tokens | Intake + relevant product docs + story |
| High-risk | ~10K tokens | Full context including templates and decisions |
```

**Acceptance criteria:**
- At least 4 context phases defined
- Phase × lane matrix is complete (no blank cells)
- At least 5 retrieval triggers documented
- Token budget guidance is concrete (not just "read less for tiny tasks")
- AGENTS.md is updated to reference CONTEXT_RULES.md
- Does not break existing agent behavior (additive, not replacing)

**Lane:** Normal

**Benchmark impact:**
- **Lane accuracy:** Should improve (agents read the right docs to classify correctly)
- **Harness compliance:** Should improve (agents know when to create stories, decisions, etc.)
- **Trace quality:** Indirect improvement (agents know to read TRACE_SPEC.md during trace phase)
- **Token cost:** May increase slightly (~5-10%) due to more doc reading

---

## Implementation Sequence

```
Week 1:
  US-003 Component Taxonomy     (~2-3 hours)
  US-005 Maturity Ladder        (~2-3 hours)

Week 2:
  US-004 Trace Specification    (~3-4 hours)
  US-006 Context Rules          (~3-4 hours)

Week 2-3:
  Update AGENTS.md + HARNESS.md references
  Update GLOSSARY.md with new terms
  Run benchmark against feature branch
  Compare with baseline
  Iterate if needed
```

**Total estimated effort:** ~15-20 hours across 2-3 weeks

---

## Execution Workflow

1. **Branch:** `git checkout -b feature/phase-2-observability-taxonomy main`
2. **Implement US-003 → US-005 → US-004 → US-006** (in order, each builds on the previous)
3. **Update cross-references:**
   - HARNESS.md → reference TRACE_SPEC.md in Task Loop section
   - AGENTS.md → reference CONTEXT_RULES.md
   - GLOSSARY.md → add terms: "component taxonomy", "maturity level", "trace quality tier", "context phase", "retrieval trigger"
4. **Run benchmark:**
   - Reset benchmark repo to `benchmark-v1` tag
   - Install harness from feature branch
   - Run `./benchmark/run.sh --agent codex --harness feature/phase-2-observability-taxonomy`
5. **Compare:** `./benchmark/compare.sh baseline-main phase-2`
6. **Iterate:** If trace quality or compliance didn't improve, adjust specs and re-run
7. **Merge:** Only when benchmark shows meaningful improvement

---

## Expected Benchmark Deltas

| Metric | Baseline (current) | Phase 2 Target | Why |
|--------|-------------------|----------------|-----|
| Functional score | 35/35 (100%) | 35/35 (100%) | Phase 2 is docs, not code quality |
| Harness compliance | ~74% (delta-based) | 85-90% | Clearer expectations → more complete task loops |
| Trace quality | 1.5 / 3.0 | 2.0-2.5 / 3.0 | Trace spec tells agents exactly what to record |
| Lane accuracy | 5/6 | 6/6 | Context rules guide classification |
| Friction captured | 2/6 tasks | 4-5/6 tasks | Friction protocol in trace spec |
| Wall time | ~40 min | ~42-45 min | Slight increase from more doc reading |
| Token cost | ~$15 | ~$16-17 | Slight increase from more context |

**What would signal failure:**
- Harness compliance doesn't move (specs are decorative, agents don't read them)
- Trace quality stays at 1.5 (trace spec isn't being followed)
- Functional score drops significantly (context overload hurt code quality)
- Token cost doubles (too much mandatory reading)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agents ignore new docs entirely | Medium | High | Reference new docs from AGENTS.md (the one file agents always read) |
| Too much mandatory reading slows agents | Medium | Medium | Token budget guidance; tiny tasks read almost nothing |
| Trace spec is too prescriptive | Low | Medium | Define tiers, not absolute requirements |
| Taxonomy becomes stale quickly | Medium | Low | Phase 3 adds automated staleness checks |
| Benchmark environment issues (like DNS) prevent clean comparison | Medium | High | Fix check-functional.sh pre-flight (PR #1); verify env before running |

---

## Deliverables Checklist

| # | Deliverable | Story | File |
|---|-------------|-------|------|
| 1 | Component taxonomy | US-003 | `docs/HARNESS_COMPONENTS.md` |
| 2 | Maturity ladder | US-005 | `docs/HARNESS_MATURITY.md` |
| 3 | Trace specification | US-004 | `docs/TRACE_SPEC.md` |
| 4 | Context rules | US-006 | `docs/CONTEXT_RULES.md` |
| 5 | AGENTS.md update | US-006 | `AGENTS.md` (add CONTEXT_RULES.md reference) |
| 6 | HARNESS.md update | US-004 | `docs/HARNESS.md` (add TRACE_SPEC.md reference in Task Loop) |
| 7 | GLOSSARY.md update | All | `docs/GLOSSARY.md` (new terms) |
| 8 | Benchmark comparison | — | `benchmark/runs/phase-2/` (in harness-benchmark repo) |

---

## What Phase 2 Does NOT Do

- No code changes (no CLI extensions, no schema migrations)
- No new Rust code
- No automation of harness checks
- No changes to the benchmark infrastructure itself
- No implementation of Phase 3+ features (distillation queries, batch verification, etc.)

These are explicitly Phase 3+ work that depends on Phase 2 specs being validated by the benchmark.

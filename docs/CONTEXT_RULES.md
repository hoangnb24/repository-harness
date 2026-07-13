# Context Engineering Rules

Context rules help agents decide what to read, when to read it, and when to
stop reading. `AGENTS.md` is the bounded authority entrypoint; it selects the
request class before this document expands retrieval.

The goal is not to maximize context. The goal is to put the right information
in the model for the current task phase and risk lane.

## Authority Gate

Request class determines both mutation authority and default context.

| Request class | Examples | Harness mutations | Default context |
| --- | --- | --- | --- |
| Read-only | answer, explain, review, diagnose, plan, status | None. Do not bootstrap, initialize/migrate, record intake, update durable state, or trace. | `AGENTS.md`, the exact files or output named by the request, then the smallest adjacent source needed to support the answer. |
| Change | change, build, fix | Bootstrap first, then intake, story/proof, trace, and backlog mutations as the selected lane requires. | `AGENTS.md`, `docs/FEATURE_INTAKE.md`, focused active matrix summary, then lane- and trigger-specific sources below. |

Cause and effect: a diagnosis may discover that a schema migration is missing,
but discovery alone does not authorize creating it. A subsequent request to fix
that migration is a change request, so bootstrap and intake happen before the
edit. Likewise, "review and apply fixes" is a change request because the user
explicitly requested repository edits; request outcome, not a single keyword,
sets authority.

## Context Phases

### Intake Phase

This phase applies only to change requests. Read to classify the request, find
the affected surface, and choose a lane.

| Document Or Source | Tiny | Normal | High-Risk |
| --- | --- | --- | --- |
| `AGENTS.md` | Must | Must | Must |
| `docs/FEATURE_INTAKE.md` | Must | Must | Must |
| `scripts/bin/harness-cli query matrix --active --summary` | Must | Must | Must |
| `README.md` | Should | Must | Must |
| `docs/HARNESS.md` | Should | Must | Must |
| `docs/ARCHITECTURE.md` | Skip | Should | Must |
| Relevant `docs/product/*` | Skip if unrelated | Must if product behavior changes | Must |
| Relevant `docs/stories/*` | Skip if unrelated | Must if a story exists | Must |
| `docs/decisions/*` | Skip | Should if architecture or durable rules are touched | Must |
| `docs/HARNESS_COMPONENTS.md` | Skip | Should for Harness improvements | Must for observability or benchmark work |

### Planning Phase

Read to decide the smallest safe approach and expected proof.

| Document Or Source | Tiny | Normal | High-Risk |
| --- | --- | --- | --- |
| Current files to edit | Must | Must | Must |
| `docs/templates/story.md` | Skip | Must when creating/updating a story | Should |
| `docs/templates/high-risk-story/*` | Skip | Skip unless risk escalates | Must |
| `docs/ARCHITECTURE.md` | Skip | Should for code or boundary changes | Must |
| `docs/TEST_MATRIX.md` or `scripts/bin/harness-cli query matrix` | Should | Must | Must |
| Relevant decisions | Skip | Should | Must |
| `docs/HARNESS_MATURITY.md` | Skip | Should for Harness improvements | Must for maturity or process changes |
| `docs/HARNESS_BACKLOG.md` and `scripts/bin/harness-cli query backlog` | Skip | Should if friction repeats | Must if changing Harness behavior |

### Implementation Phase

Read while making the change. Keep this phase scoped to files that directly
affect the selected story.

| Document Or Source | Tiny | Normal | High-Risk |
| --- | --- | --- | --- |
| Files being changed | Must | Must | Must |
| Adjacent files with same pattern | Should | Must | Must |
| Relevant product docs | Skip if copy-only | Must if behavior changes | Must |
| Relevant story packet | Skip if no story needed | Must | Must |
| Relevant templates | Skip | Should when adding docs | Must |
| `docs/ARCHITECTURE.md` | Skip | Should for structural changes | Must |
| Provider/API/security docs | Skip | Should if touched | Must |
| Unrelated docs and historical traces | Skip | Skip | Should only if they affect decisions |

### Validation Phase

Read to prove the change and avoid claiming unsupported completion.

| Document Or Source | Tiny | Normal | High-Risk |
| --- | --- | --- | --- |
| Story acceptance criteria | Should | Must | Must |
| `docs/TEST_MATRIX.md` or `scripts/bin/harness-cli query matrix` | Should | Must | Must |
| Validation section of story packet | Skip if no story | Must | Must |
| `docs/templates/validation-report.md` | Skip | Should for notable proof | Must for high-risk proof |
| Relevant commands from README/package docs | Should | Must | Must |
| Benchmark protocol or external benchmark repo | Skip | Skip unless requested | Must if the story depends on benchmark proof |
| `docs/HARNESS_MATURITY.md` | Skip | Should for Harness improvements | Must for maturity claims |

### Trace Phase

Read to leave useful evidence for the next agent and for benchmark scoring.

| Document Or Source | Tiny | Normal | High-Risk |
| --- | --- | --- | --- |
| `docs/TRACE_SPEC.md` | Should | Must | Must |
| `scripts/bin/harness-cli query matrix` | Should | Must | Must |
| `scripts/bin/harness-cli query backlog` | Skip | Should if friction occurred | Must |
| Changed-file list from `git status --short` | Must | Must | Must |
| Validation command output | Should | Must | Must |
| Story packet or progress log | Skip if no story | Must | Must |
| `docs/HARNESS_COMPONENTS.md` | Skip | Should if attributing friction | Must if failure attribution is needed |

## Retrieval Triggers

| Trigger Condition | Action |
| --- | --- |
| Task touches database schema, durable records, or migrations | Read `docs/decisions/0004-sqlite-durable-layer.md`, `scripts/schema/`, and relevant CLI code before planning. |
| Task touches CLI command behavior or installer distribution | Read `docs/decisions/0005-prebuilt-rust-harness-cli.md`, `scripts/README.md`, relevant `crates/harness-cli/*` code, CLI help output, and installer docs. |
| Task touches auth, authorization, audit/security, data loss, or external providers | Treat as high-risk, read `docs/templates/high-risk-story/*`, and check prior decisions before implementation. |
| Task changes public API shape, product behavior, or user-visible workflow | Read relevant `docs/product/*`, story packets, and validation expectations before editing. |
| Task changes Harness policy, source hierarchy, risk classification, or validation requirements | Read `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, `docs/ARCHITECTURE.md`, and `docs/decisions/*`; pause if direction is ambiguous. |
| Task discovers repeated confusion, stale docs, or missing proof | Read `docs/HARNESS_BACKLOG.md`, record `harness_friction`, and add a backlog item when the fix is out of scope. |
| Task makes a maturity, observability, trace quality, or benchmark claim | Read `docs/HARNESS_COMPONENTS.md`, `docs/HARNESS_MATURITY.md`, and `docs/TRACE_SPEC.md`. |
| Task is normal or high-risk and spans multiple iterations | Create or update a story/progress file under `docs/stories/` and keep it current. |
| A change-request final response is being prepared | Re-read the validation evidence, `git status --short`, and `docs/TRACE_SPEC.md` before recording the final trace. |

## Token Budget Guidance

| Lane | Target Context Budget | Read Shape | Reasoning |
| --- | --- | --- | --- |
| Tiny | About 2K tokens of Harness context | `AGENTS.md`, `docs/FEATURE_INTAKE.md`, focused active matrix summary, and the exact file being changed. | Tiny work should not spend more context on policy than on the edit. |
| Normal | About 5K tokens of Harness context | Intake docs, relevant product/story docs, architecture when structural, validation expectations, and trace spec at the end. | Normal work needs enough context to preserve contracts and record proof without reading every historical file. |
| High-risk | About 10K tokens of Harness context | Full intake, architecture, relevant decisions, high-risk templates, product docs, validation docs, trace spec, and component/maturity docs when Harness behavior changes. | High-risk work needs source hierarchy, prior decisions, and proof expectations in context before implementation. |

Budget rules:

- Prefer targeted `rg` searches over bulk reading.
- Read the smallest section that answers the current phase question.
- Escalate context when a retrieval trigger fires.
- Do not keep reading unrelated history after the lane, affected files, and
  validation path are clear.

## Bounded Retrieval Behavior

Do not preload every Harness document. For a read-only request, stop after the
answer is supported. For a change request, `AGENTS.md` points to intake and the
focused matrix summary; this document then expands context only when a lane,
phase, or retrieval trigger requires it.

## Review Checklist

Before implementation of a change request:

- Lane is chosen from `docs/FEATURE_INTAKE.md`.
- Relevant product docs or story packets are identified.
- Any high-risk trigger has been handled.

Before the final response for a change request:

- Validation evidence has been read.
- `docs/TRACE_SPEC.md` has been read for normal/high-risk tasks.
- The final trace includes files read, files changed, outcome, and friction
  when applicable.

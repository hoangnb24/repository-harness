# Context Engineering Rules

What to read, when to read it, and when to stop. Additive to the stable
`AGENTS.md` reading order — `AGENTS.md` lists the entrypoints every task reads;
this file says what to retrieve *after* that, based on the WORKFLOW stage and
the lane.

The goal is not maximum context. It is putting the right information in the
model for the current stage at the lowest token cost.

> Pairs with `.claude/hooks/context-monitor.sh`: the hook tells you **how much**
> context you have spent (40/60/80/95% warnings); this file tells you **what**
> is worth spending it on. When the hook warns, stop reading anything this file
> marks Skip for your stage.

## Reading By Stage Group

The 13 WORKFLOW stages collapse into five context phases. Read the column for
your lane. `self-review` (the default) follows the **Normal** column unless a
risk-checklist flag escalates it to **High-risk**.

### Discovery & Intake — Stages 1–4 (lead, intake brief, discovery, SOW)

| Source | Tiny | Normal / Self-review | High-risk |
| --- | --- | --- | --- |
| `STAGE.md` | Must | Must | Must |
| `AGENTS.md` + `docs/FEATURE_INTAKE.md` | Must | Must | Must |
| `docs/discovery/*` (raw client inputs) | Should | Must | Must |
| `docs/intake/*` (prior briefs this project) | Skip | Must | Must |
| `docs/WORKFLOW.md` (stage detail) | Should | Must | Must |
| Stage playbook (discovery-interview, gap-analysis) | Skip | Must | Must |
| `docs/HARNESS.md` § Spec Lifecycle | Skip | Should | Must |

### Spec & Modeling — Stages 5–6 (spec intake, visual & behavioral modeling)

| Source | Tiny | Normal / Self-review | High-risk |
| --- | --- | --- | --- |
| `docs/intake/*` + SOW + `docs/discovery/*` | Skip | Must | Must |
| `docs/templates/spec-intake.md` | Skip | Must | Must |
| `docs/ARCHITECTURE.md` § Discovery Before Shape | Skip | Should | Must |
| `docs/playbooks/ui-design-system-contract.md` (UI work) | Skip | Must if UI | Must if UI |
| `docs/playbooks/visual-and-behavioral-modeling.md` | Skip | Must | Must |
| Prior `docs/decisions/*` (stack, design-direction) | Skip | Should | Must |

### Slicing & Build — Stages 7–8 (story slicing, build)

| Source | Tiny | Normal / Self-review | High-risk |
| --- | --- | --- | --- |
| Files being changed | Must | Must | Must |
| `docs/templates/story.md` | Skip | Must | Should |
| `docs/templates/high-risk-story/*` | Skip | Skip unless risk escalates | Must |
| `docs/product/*` for the touched behavior | Skip if copy-only | Must | Must |
| `docs/TEST_MATRIX.md` (existing proof + gaps) | Should | Must | Must |
| `docs/playbooks/scenario-taxonomy-playbook.md` | Skip | Must when slicing | Must |
| `docs/ARCHITECTURE.md` + relevant decisions | Skip | Should for structural change | Must |

### Review, QA & Acceptance — Stages 9–11 (code review, QA, UAT/signoff)

| Source | Tiny | Normal / Self-review | High-risk |
| --- | --- | --- | --- |
| Story acceptance criteria + REQ/SC tokens | Should | Must | Must |
| `docs/TEST_MATRIX.md` (incl. Verify / Last verified) | Should | Must | Must |
| `docs/playbooks/code-review-scoring.md` | Skip | Must at review | Must |
| `docs/playbooks/canonical-e2e-flow-playbook.md`, `e2e-qa-field-by-field-verify-with-report.md` | Skip | Must at QA | Must |
| `docs/FEATURE_INTAKE.md` § Pre-Close Verification Gate | Should | Must | Must |
| `docs/templates/delivery-closure-story/*` | Skip | Must at UAT | Must |

### Release & Handover — Stages 12–13

| Source | Tiny | Normal / Self-review | High-risk |
| --- | --- | --- | --- |
| `docs/templates/release-note.md` | Skip | Must | Must |
| `docs/templates/deployment-guide.md` / `docs/deployment-guide.md` | Skip | Must at first deploy | Must |
| `docs/templates/project-closure-story/*` + `maintenance-proposal.md` | Skip | Must at handover | Must |
| `docs/TRACE_SPEC.md` (record the session trace) | Should | Must | Must |

## Retrieval Triggers

Fire these regardless of stage when the condition appears:

| Trigger | Action |
| --- | --- |
| Task changes architecture, auth, data ownership, API shape, or validation rules | Treat as high-risk. Read `docs/templates/high-risk-story/*` and prior `docs/decisions/*` before implementing. Write a `docs/decisions/NNNN-*.md` before closing. |
| First implementation story of a new buildout | Confirm a stack-selection decision exists; if not, apply `docs/ARCHITECTURE.md` § Discovery Before Shape first (`AGENTS.md` Task Loop step 6). |
| Work touches a UI / visual surface | Read `docs/design-guidelines.md` + `docs/playbooks/ui-design-system-contract.md` § Component Coverage Matrix (`AGENTS.md` step 7). |
| Hitting a familiar tooling / environment symptom | Scan `docs/playbooks/README.md` for a recipe before re-deriving (`AGENTS.md` step 5). |
| Repeated confusion, stale doc, or missing proof | Record friction per `docs/TRACE_SPEC.md`; add a `docs/HARNESS_BACKLOG.md` item if the fix is out of scope. |
| Preparing the final response | Re-read validation evidence + `git status --short` + `docs/TRACE_SPEC.md` review checklist. |

## Token Budget Guidance

| Lane | Target harness context | Read shape |
| --- | --- | --- |
| Tiny | ~2K tokens | `STAGE.md`, `FEATURE_INTAKE.md`, the exact file changed. |
| Normal / Self-review | ~5K tokens | Stage-group table above + the touched story/product docs + TEST_MATRIX + trace spec at the end. |
| High-risk | ~10K tokens | Full stage-group + architecture + relevant decisions + high-risk templates + trace spec. |

Budget rules:
- Prefer targeted `rg`/`grep` over bulk file reads.
- Read the smallest section that answers the current stage's question.
- When `context-monitor.sh` warns at 80%, stop reading Skip-marked sources and
  move to producing the stage artifact.
- The `stage-runner` subagent runs a stage in its own context — delegate to it
  (`/stage-next`) so heavy stage reading never lands in the main session
  (`AGENTS.md` § Stage Orchestration).

## Review Checklist

Before producing a stage artifact:
- Lane is set in `STAGE.md`; stage matches `STAGE.md` Current.
- The stage-group reading column for the lane has been satisfied.
- Any high-risk trigger has been handled.

Before final response:
- Validation evidence read; Verify command run if the story carries one.
- `docs/TRACE_SPEC.md` consulted for the session trace (normal/high-risk).

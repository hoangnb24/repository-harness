# Feature Intake

Every implementation prompt enters the intake gate before code changes. A new
project spec also enters through this gate before it becomes product docs,
stories, or implementation work.

The human does not need to classify risk. The harness does.

**Default lane:** `self-review`. The human plays the role of the customer at
every stage and uses each artifact as a comprehension/approval gate. All 13
WORKFLOW.md stages are required — no stage skips. Legacy `tiny | normal |
high-risk` lanes remain available for teams that explicitly opt out, but the
self-review lane is what the harness assumes when nothing else is declared.
See `docs/decisions/0013-self-review-lane-and-stage-tracker.md`.

## Intake Flow

```text
User prompt
    |
    v
Classify input type
    |
    v
Restate as work item
    |
    v
Find affected product docs and stories
    |
    v
Run risk checklist
    |
    v
Choose lane: self-review (default) | tiny | normal | high-risk
    |
    v
Update STAGE.md current stage row when a stage completes
```

## Input Types

Use the input type to decide where the work should land before choosing the risk
lane.

| Type | Use when | Typical artifact |
| --- | --- | --- |
| New spec | Turning a user-provided project spec into harness-ready docs | Product docs, candidate epics, decisions |
| Spec slice | Implementing selected behavior from an accepted spec | Story packet |
| Change request | Changing, fixing, or refining accepted behavior | Story packet or direct patch |
| New initiative | Adding a larger product area that needs multiple stories | Initiative notes plus story packets |
| Maintenance request | Changing technical, operational, or dependency behavior | Story packet, validation report, or decision |
| Harness improvement | Improving how humans and agents collaborate | Direct docs update or `docs/HARNESS_BACKLOG.md` |

Do not create or extend a monolithic spec by default after intake. Use product
docs, stories, decisions, and initiative notes as the living surface.

## Lanes

### Self-Review (default)

Use whenever the human wants to act as the customer and review every artifact
the harness produces. This is the default for AI-generated projects where the
human is the only quality gate.

Requirements:

- **All 13 WORKFLOW.md stages run.** No skipping. The Per-Tier Stage Matrix's
  "skip" cells do not apply.
- Stage artifacts are produced for human review even if the artifact is small
  (e.g. greenfield with no As-Is still gets a one-line gap-analysis note
  saying so, rather than skipping stage 3.B entirely).
- Each stage completion updates `STAGE.md` at the repo root and lands a
  stage-boundary commit per `docs/decisions/0012-stage-boundary-commits.md`.
- Validation rigor scales with risk-checklist flags below — depth changes,
  but stage coverage does not.

When NOT to use:

- Mid-flight project that already operates under tiny/normal/high-risk —
  do not retrofit.
- The human has explicitly delegated quality to another role (paid QA,
  external reviewer) and does not need every stage as a comprehension gate.

### Tiny

Use for low-risk docs, copy, names, or narrow edits.

Requirements:

- Patch directly.
- Keep affected docs current.
- Run available quick checks.
- Update the harness only if friction was found.

### Normal

Use for story-sized behavior with bounded blast radius.

Requirements:

- Create or update one story file from `docs/templates/story.md`.
- Link relevant product docs.
- Add or update validation expectations.
- Implement the smallest vertical slice when implementation exists.
- Update `docs/TEST_MATRIX.md`.

### High-Risk

Use when the work can affect security, data, scope, contracts, or multiple
roles/platforms.

Requirements:

- Create a story folder using `docs/templates/high-risk-story/`.
- Fill in `execplan.md`, `overview.md`, `design.md`, and `validation.md`.
- Ask for human confirmation before implementation if direction is ambiguous.
- Record a decision when behavior or architecture changes meaningfully.
- For release-time closure (any lane), reach for `docs/templates/delivery-closure-story/` (overview + UAT plan + signoff + client update).
- For end-of-project handover (ownership change), reach for `docs/templates/project-closure-story/` (overview + handover docs + credentials handover + knowledge transfer).

## Risk Checklist

Mark one flag for each item that applies:

| Risk flag | Applies when the work touches |
| --- | --- |
| Auth | login, logout, sessions, JWT, password, refresh token |
| Authorization | roles, permissions, tenant or company scope |
| Data model | schema, migrations, uniqueness, deletion, retention |
| Audit/security | audit logs, privacy, sensitive data, access logs |
| External systems | email, payments, cloud services, provider SDKs, queues, webhooks |
| Public contracts | API shape, response envelope, client-visible behavior |
| Cross-platform | desktop/mobile/browser split, native shell behavior, deep links |
| Existing behavior | already implemented or test-covered behavior changes |
| Weak proof | unclear or missing tests around the affected area |
| Multi-domain | more than one product domain changes at once |

## Classification

Self-review is the default — flag count below changes validation *depth* per
stage, not which stages run. Only opt into tiny/normal/high-risk when a stage
genuinely does not apply (and document that decision in `STAGE.md`).

```text
self-review (default):
  all 13 stages required; flags below tune depth, not coverage

0-1 flags:
  light depth — artifacts may be one-paragraph notes

2-3 flags:
  standard depth — full template use, validation expected

4+ flags:
  strict depth — high-risk-story packet, 2 reviewers, RPM + Status Flow per entity

Any hard gate:
  strict depth + explicit decision doc, regardless of opt-in lane
```

Legacy lane mapping (only if the human explicitly opts out of self-review):

```text
0-1 flags  → tiny or normal
2-3 flags  → normal with stronger validation
4+ flags   → high-risk
hard gate  → high-risk unless human narrows scope
```

Hard gates:

- Auth.
- Authorization.
- Data loss or migration.
- Audit/security.
- External provider behavior.
- Removing or weakening validation requirements.

## Spec Approval Gate (New Spec input type only)

A new spec is the highest-leverage input — misinterpretation propagates
across every story, decision, and component that follows. For the
**New Spec** input type only, intake is **two phases with a human gate
between them**.

**What "the spec" means here:** there is no single `SPEC.md` file. The
spec is the **aggregate** of:

- All raw input artifacts under `docs/discovery/` (client-provided spec
  PDF/markdown, brainstorm notes the vendor wrote with ChatGPT/Claude,
  meeting transcripts, mockup screenshots, sample data exports). See
  `docs/decisions/0009-discovery-input-folder-convention.md`.
- Any vendor-produced intake artifacts already under `docs/intake/`
  (intake-brief from stage 2, discovery-summary from stage 3.A,
  gap-analysis from stage 3.B if applicable).
- The signed SOW from stage 4 (paid client work only).

The agent reads all of the above as Phase 1 input.

1. **Phase 1 — Read + restate.** Save the output as
   `docs/intake/YYYY-MM-DD-spec-intake.md` using
   `docs/templates/spec-intake.md`: project summary, candidate product
   docs, candidate epics, architecture questions, validation shape,
   first story candidates. Use `docs/playbooks/discovery-interview-playbook.md`
   as the canonical interview shape when the spec needs structured probing.
2. **Stop.** Present the intake doc to the human. Do NOT start
   deriving `docs/product/*`, architecture decisions, design-direction
   decisions, or story packets yet.
3. **Phase 2 — Derive.** Only after human approves the intake (any of:
   "approved", "looks good", "proceed", or specific corrections then
   approval), proceed to derive product docs, architecture decision
   (use `docs/templates/decisions/stack-selection.md` for the stack
   decision), design-direction decision, and first story packets.

Other input types (spec slice, change request, maintenance, etc.) skip
this gate — they're bounded enough to proceed straight to lane work.

## Pre-Close Verification Gate

The Spec Approval Gate guards the **front** of the work (did we understand the
request?). This gate guards the **back** (did the work actually meet its
contract?). It is the mechanical half of "done" — adapted from the upstream
story-verify concept, kept instruction-level for this fork
(`docs/decisions/0014-distill-upstream-observability-concepts.md`).

A story, stage, or change cannot be marked **done / closed** until one of:

1. Its **Verify command** in `docs/TEST_MATRIX.md` § Verification Register was
   run and `Result` is `pass`, recorded with today's date; **or**
2. The story packet (or TEST_MATRIX row) explains why no command exists —
   pure-docs, design-only, or a `MANUAL:` checkpoint the human signed off
   (cite the signoff: UAT row, `delivery-closure-story/02-signoff.md`, or a
   checkpoint date).

When a stage boundary closes (`docs/decisions/0012`), the `Last verified` +
`Result` update lands in the **same commit** as the stage artifact and the
`STAGE.md` row move. Closing a story with `Result: never-run` and no recorded
reason is a gate violation — fix before reporting done.

Per lane:

| Lane | Gate behavior |
| --- | --- |
| Tiny | Soft. Inline narrative proof is enough; a `MANUAL:` note is acceptable. |
| Normal / Self-review | Required. Verify command run + `pass`, or recorded reason. The human-as-customer uses this as the comprehension gate. |
| High-risk | Required + a `docs/decisions/NNNN-*.md` record when the change touched architecture, auth, data ownership, API shape, or validation rules. |

This gate is enforced **mechanically** by a git hook (`.githooks/pre-commit` +
`pre-push`, core `scripts/hooks/harness-verify-gate.sh`, activated via
`core.hooksPath` by the installer). The hook runs the project's lint/validate
command and blocks any `Result: fail` in the Verification Register — and
`never-run` on a stage-close commit. Agents must not bypass it with
`--no-verify`; that override is human-only with a stated reason
(`AGENTS.md` § Verify Gate — No Bypass). The human reviewing `STAGE.md` + the
Register remains the second line. See
`docs/decisions/0014-distill-upstream-observability-concepts.md`.

## Output

At the end of intake, the agent should be able to say:

```text
Lane: self-review (default)
Depth: standard (3 risk flags — authorization, API contract, audit).
Docs: permissions, account-settings, audit-log.
Story: docs/stories/epics/E02-access-control/US-014-manager-updates-role.md.
Validation: unit, integration, E2E.
Next stage: 6 — Visual & Behavioral Modeling (update STAGE.md on completion).
```

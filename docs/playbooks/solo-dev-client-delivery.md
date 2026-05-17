# Solo-Dev Client Delivery Playbook

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Meta-playbook for solo developers (or small teams) delivering paid work to clients with the harness. Maps each commercial stage to existing harness artifacts. **Pointers only — no new mechanics.** Honor `playbook-composition-pattern.md`: this composes, it does not duplicate.

## When To Run

- First time using the harness for a paid client project.
- Re-orienting at any stage during an active client project ("where am I in the flow, what do I owe next?").
- Onboarding a new collaborator into the commercial side of a project.

Skip when:

- The project is internal / OSS / hobby — most commercial wrappers are noise. Use the harness directly from `docs/FEATURE_INTAKE.md`.
- The project is mid-flight and the team already has a working delivery cadence — do not retrofit ceremony.

## The Flow

Thirteen stages. Each stage points to ONE primary artifact and 0-2 supporting playbooks.

```text
[1. Lead] → [2. Intake brief] → [3. Discovery] → [4. Proposal/SOW] →
[5. Spec intake + Design intake] → [6. Visual & Behavioral Modeling] →
[7. Story slicing] → [8. Build] → [9. Code review] → [10. QA + scenarios]
  → [11. UAT + signoff] → [12. Release + client update]
  → [13. Handover + maintenance]
```

### 1. Lead

A potential client reaches out. Capture the conversation in any form (email thread, chat log, meeting notes). No artifact yet.

### 2. Intake brief

Vendor-internal one-pager: should we take this project?

- **Artifact:** `docs/templates/client-intake-brief.md` (`locale-vi/` fork if client-facing).
- **Decide:** proceed-to-discovery / proceed-with-conditions / park / decline.
- **Output (vendor-produced):** a saved brief at `docs/intake/YYYY-MM-DD-intake-brief.md` per `docs/intake/README.md`.
- **Inputs (raw, from client):** any source docs, emails, prior proposals — file under `docs/discovery/YYYY-MM-DD-<slug>.{ext}` per `docs/discovery/README.md`.

If declining, send the polite reply (§ 15 of the brief) and stop.

### 3. Discovery

Two sub-steps. 3.A surfaces what the client said; 3.B structures what it means.

#### 3.A — Discovery interview

Structured conversation to surface REQs, decisions, and open questions.

- **Playbook:** `docs/playbooks/discovery-interview-playbook.md` (5 personas × 3 modes).
- **Output (vendor-produced):** REQ list, decisions log, open questions list. Save to `docs/intake/YYYY-MM-DD-discovery-summary.md` per `docs/intake/README.md`.
- **Inputs (raw, from session):** meeting recording / notes / screenshots → `docs/discovery/YYYY-MM-DD-<slug>.{ext}`.
- **Time-box:** 60-90 min for spec intake; 20-30 min for change requests.

#### 3.B — Gap analysis (BA technique)

Compare As-Is vs To-Be, identify gaps, propose solutions. Outputs feed SOW § 4 in-scope decisions directly.

- **Playbook:** `docs/playbooks/gap-analysis.md` (4-step BA technique).
- **Template:** `docs/templates/gap-analysis.md` (`locale-vi/` fork for client-facing).
- **Output (vendor-produced):** `docs/intake/YYYY-MM-DD-gap-analysis.md` with To-Be / As-Is / Gap (6 categories) / Plan of Action (MoSCoW).
- **Gate:** vendor-draft round 1 → client review → freeze before SOW § 4 finalizes.
- **Per-tier:** tiny = skip; normal = required when client has existing systems or processes being replaced; high-risk = required + stakeholder validation round.
- **Skip when:** greenfield (no As-Is) or pure refactor / migration (technical, document in a decision instead).

### 4. Proposal & SOW

Convert the discovery output into a priced commercial proposal.

- **Artifact:** `docs/templates/proposal-sow.md` (`locale-vi/` fork for client-facing).
- **Critical sections:** § 4 in-scope, § 5 out-of-scope, § 7 milestones, § 8 payment schedule, § 9 change-request policy, § 10 acceptance conditions.
- **Gate:** signed SOW + deposit before any code is written.

### 5. Spec intake + Design intake

After signing, derive harness artifacts from the spec.

- **Artifact:** `docs/templates/spec-intake.md`. Triggers `docs/product/*` derivation.
- **Gate:** human approves the intake before Phase 2 (`docs/FEATURE_INTAKE.md` § Spec Approval Gate).
- **UI projects also run:** `docs/playbooks/ui-design-system-contract.md` § Style Intake (5 sources). Produce `docs/decisions/YYYY-MM-DD-design-direction.md` then `docs/design-guidelines.md`.
- **High-risk projects also write:** `docs/decisions/NNNN-stack-selection.md` (per `docs/ARCHITECTURE.md` § Discovery Before Shape).

### 6. Visual & Behavioral Modeling

Build the visual + behavioral contract BEFORE slicing stories. Triple-use: client review surface, AI code-generation handoff target, UAT pass criterion.

- **Artifact:** `docs/playbooks/visual-and-behavioral-modeling.md` (3 sub-steps).
  - **A. Design system check** — confirm `docs/design-guidelines.md` from stage 5 covers prototype components.
  - **B. Interactive prototype** — generate with Claude Design (https://claude.ai/design) → fallback ladder: `/stitch` skill → Claude Artifacts → v0.dev → pencil.dev/penpot. Output under `docs/visuals/prototype/`.
  - **C. Business diagrams** — Sitemap, User Flow per journey, Business Workflow, ERD draft, Role-Permission Matrix, Status Flow (per stateful entity). Outputs under `docs/visuals/diagrams/`.
- **Templates:** `docs/templates/role-permission-matrix.md` and `docs/templates/status-flow.md` (`locale-vi/` forks for client-facing).
- **Gate:** prototype + all diagrams frozen before stage 7. Client confirms prototype in writing.
- **Per-tier:** tiny = skip whole stage; normal = sub-step A + sitemap + 1 user flow + 1 prototype screen per client-visible surface; high-risk = all sub-steps + RPM + Status Flow per stateful entity.

### 7. Story slicing

Cut product surface into story-sized work.

- **Artifact:** `docs/stories/epics/EXX-name/US-NNN-name.md` (from `docs/templates/story.md`). High-risk lane uses `docs/templates/high-risk-story/`.
- **Tokens:** every REQ becomes `US-NNN.REQ-MMM`. Every test scenario becomes `US-NNN.SC-MMM`.
- **Scenario decomposition:** for each REQ, run `docs/playbooks/scenario-taxonomy-playbook.md` (12 dimensions).
- **Inputs from stage 6:** RPM grid cells citing REQ tokens become acceptance criteria; status-flow transitions become SC scenarios.

### 8. Build

Execute the story. Honour the story's § Implementation Guardrails section.

- **Artifact:** the code itself + commits referencing the story / REQ tokens.
- **Discipline:** don't change architecture without a new decision doc. Don't delete code without justification. Handle loading / error / empty states for any UI surface. Explain what changed in the commit body.
- **Rule:** every commit cites at least one `US-NNN.REQ-MMM` or `US-NNN.SC-MMM` token in the message.

### 9. Code review

Per-tier rubric.

- **Artifact:** `docs/playbooks/code-review-scoring.md` (6-dim, pass threshold ≥ 7, any 0 auto-blocks).
- **Application:** tiny = optional, normal = 1 reviewer, high-risk = 2 reviewers.

### 10. QA + scenarios

Prove the story behaves.

- **Artifacts:** `docs/TEST_MATRIX.md` rows citing `US-NNN.TC-MMM`; `docs/playbooks/canonical-e2e-flow-playbook.md` for user-journey tests.
- **Bug-for-tutorial flow:** `docs/playbooks/e2e-qa-field-by-field-verify-with-report.md` when the same artifact must also serve as a user-guide demo.
- **Rule:** every `REQ` cited in a story must trace to at least one `TC` row in TEST_MATRIX before UAT.

### 11. UAT + signoff

Client-facing acceptance gate. This is where harness rigor meets commercial reality.

- **Artifacts (English defaults; `locale-vi/` for client deliverables):**
  - `docs/templates/delivery-closure-story/overview.md` — wrapper story.
  - `docs/templates/delivery-closure-story/01-uat-plan.md` — TC table with ≤ 40 cases.
  - `docs/templates/delivery-closure-story/02-signoff.md` — REQ coverage + exclusions + conditions.
  - `docs/templates/delivery-closure-story/03-client-update.md` — message sent to the client.
- **Gate:** REQ coverage complete (every `US-NNN.REQ-MMM` either passed or explicitly excluded with a decision link).
- **Visual gate:** "live product matches frozen prototype from stage 6" is an explicit pass criterion. Drift documented in change-request log if accepted, or in the bug list if rejected.

### 12. Release + client update

Production deploy + structured client communication.

- **Artifact:** `docs/templates/release-note.md` (`locale-vi/` fork for client-facing).
- **Sub-checklists in the template:** § 7 pre-deploy checklist, § 8 post-deploy smoke, § 9 rollback plan, § 11 client-update message.
- **Rule:** every released REQ token appears in the release note. Every deferred REQ links to a follow-up story or backlog row.

### 13. Handover + maintenance

End-of-project ownership change + recurring revenue offer.

- **Artifacts (English defaults; `locale-vi/` for client deliverables):**
  - `docs/templates/project-closure-story/overview.md` — wrapper.
  - `docs/templates/project-closure-story/01-handover-docs.md` — index of read-this-order.
  - `docs/templates/project-closure-story/02-credentials-handover.md` — vault-pointer credentials checklist (no raw secrets).
  - `docs/templates/project-closure-story/03-knowledge-transfer.md` — sessions log.
- **Stage-6 artifacts also ship** as part of handover: `docs/visuals/prototype/` URL + screen exports, `docs/visuals/diagrams/*`, frozen RPM, frozen status flows.
- **Then:** send `docs/templates/maintenance-proposal.md` (`locale-vi/` fork). Defines SLA, tiers, and post-warranty support process.

## Always-On: Change Request

Independent of stage. Any client request that lands after SOW signing enters the log.

- **Artifact:** `docs/templates/change-request-log.md` (`locale-vi/` fork for client visibility).
- **Trigger:** new request from any channel. Even verbal asks.
- **Process:** classify (bug / change-request / new-feature / ux-improvement / clarification) → in-scope check → effort estimate (if non-bug) → reply using template (§ Reply Templates).

## Always-On: Audit Trail

- Every signed-off REQ has at least one TC row in `docs/TEST_MATRIX.md`.
- Every deviation from SOW lives in `docs/templates/change-request-log.md`.
- Every architecture change has a `docs/decisions/NNNN-*.md`.
- Every multi-task session ends with `docs/playbooks/session-retrospective.md` written to `plans/reports/retro-<date>-<slug>.md`.

## Decision Matrix — Which Templates Apply

| Project type | Intake brief | SOW | Spec intake | Design intake | Visual modeling | High-risk story | Maintenance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Landing page (Low) | yes | yes | optional | yes | partial (prototype + sitemap) | no | optional |
| Web app / SaaS (Medium) | yes | yes | yes | yes | yes (RPM if multi-role) | optional | yes |
| Internal tool / automation (Medium) | yes | yes | yes | optional | yes (RPM + status flow) | optional | yes |
| AI app (Medium) | yes | yes | yes | optional | partial (prototype + flows) | yes (if user-data) | yes |
| E-commerce / Dashboard (High) | yes | yes | yes | yes | yes (all sub-steps) | yes | yes |
| Mobile (Medium-High) | yes | yes | yes | yes | yes (all sub-steps) | optional | yes |

## When This Playbook Conflicts With The Harness

The harness wins. This playbook is a *commercial wrapper around* the harness — when a step here implies skipping a harness rule, the harness rule applies. Specifically:

- Cannot skip `docs/FEATURE_INTAKE.md` § Spec Approval Gate even under timeline pressure.
- Cannot skip stack-selection decision (`docs/ARCHITECTURE.md` § Discovery Before Shape) before the first implementation story.
- Cannot skip `docs/playbooks/code-review-scoring.md` for normal/high-risk lanes even when the client is "fine without review".
- Cannot replace `docs/TEST_MATRIX.md` with "UAT will catch it" — UAT TCs cite matrix rows; the matrix is the source of truth.
- Cannot regenerate the stage-6 prototype post-freeze to "match the code" — drift goes through `change-request-log.md` and a documented decision, not a silent re-render.

## Variant Section

(Append a Variant block here when this playbook fails or partially works. Do not delete the original shape.)

## Related

- `docs/playbooks/playbook-composition-pattern.md` — composition rules this playbook honors.
- `docs/playbooks/bilingual-delivery-template-pattern.md` — locale fork pattern used by the client-facing artifacts above.
- `docs/playbooks/discovery-interview-playbook.md` — stage 3.A.
- `docs/playbooks/gap-analysis.md` — stage 3.B.
- `docs/playbooks/ui-design-system-contract.md` — stage 5 (UI projects).
- `docs/playbooks/visual-and-behavioral-modeling.md` — stage 6.
- `docs/playbooks/scenario-taxonomy-playbook.md` — stage 7.
- `docs/playbooks/code-review-scoring.md` — stage 9.
- `docs/playbooks/canonical-e2e-flow-playbook.md` — stage 10.
- `docs/playbooks/session-retrospective.md` — end-of-session capture.
- `docs/templates/proposal-sow.md`, `client-intake-brief.md`, `maintenance-proposal.md`, `release-note.md`, `change-request-log.md` — commercial templates this playbook chains.
- `docs/templates/gap-analysis.md` — stage-3.B template.
- `docs/templates/role-permission-matrix.md`, `status-flow.md` — stage-6 templates.
- `docs/templates/delivery-closure-story/`, `project-closure-story/` — closure templates this playbook chains.
- `docs/decisions/0007-solo-dev-client-delivery-templates.md` — original commercial-wrapper decision.
- `docs/decisions/0008-visual-behavioral-modeling-stage.md` — stage-6 insertion decision.
- `docs/decisions/0010-gap-analysis-stage.md` — stage-3.B gap analysis decision.

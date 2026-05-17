# Workflow

Visual map of the 13-stage solo-dev paid-client delivery flow. Each stage shows the playbook that runs it, the template/artifact shape, the decision that authorised the stage, the gate/hook that controls progression, and where output lands.

**Authority:** `docs/playbooks/solo-dev-client-delivery.md` is the source of truth. This file is a navigation aid — when they disagree, the meta-playbook wins.

**Scope:** solo-dev paid client work. Internal / OSS / hobby projects skip this flow and use `docs/FEATURE_INTAKE.md` lanes directly.

## TL;DR Flow

```text
[1. Lead] → [2. Intake brief] → [3. Discovery]
   ├─ 3.A Interview
   └─ 3.B Gap Analysis
→ [4. Proposal & SOW] → [5. Spec + Design intake]
→ [6. Visual & Behavioral Modeling]
→ [7. Story slicing] → [8. Build] → [9. Code review]
→ [10. QA + scenarios] → [11. UAT + signoff]
→ [12. Release + client update] → [13. Handover + maintenance]
```

Always-on across all stages:

- **Change Request** — any post-SOW client request → `docs/templates/change-request-log.md`.
- **Audit trail** — every architecture choice → `docs/decisions/NNNN-*.md`; every multi-task session end → `docs/playbooks/session-retrospective.md`.
- **Discovery inputs** — anything received raw from client → `docs/discovery/YYYY-MM-DD-<slug>.{ext}` (append-only).
- **Intake briefs** — anything vendor produces analysing inputs → `docs/intake/YYYY-MM-DD-<artifact>.md`.

## Stage-By-Stage Map

| # | Stage | Playbook | Template | Decision | Gate / Hook | Output |
|---|---|---|---|---|---|---|
| 1 | Lead | — | — | — | none | conversation captured anywhere |
| 2 | Intake brief | — | `client-intake-brief.md` (`locale-vi/`) | 0007 | accept / decline / park | `docs/intake/YYYY-MM-DD-intake-brief.md` |
| 3.A | Discovery interview | `discovery-interview-playbook.md` | — | — | 5 personas × 3 modes covered | `docs/intake/YYYY-MM-DD-discovery-summary.md` |
| 3.B | Gap analysis (As-Is vs To-Be) | `gap-analysis.md` | `gap-analysis.md` (`locale-vi/`) | 0010 | client review round → freeze | `docs/intake/YYYY-MM-DD-gap-analysis.md` |
| 4 | Proposal & SOW | — | `proposal-sow.md` (`locale-vi/`) | 0007 | signed SOW + deposit | client-shared SOW PDF / link |
| 5 | Spec + Design intake | `ui-design-system-contract.md` § Style Intake | `spec-intake.md` + `design-direction` decision | 0003, 0005 | Spec Approval Gate (`FEATURE_INTAKE.md`) | `docs/product/*`, `docs/design-guidelines.md`, stack-selection decision |
| 6 | Visual & Behavioral Modeling | `visual-and-behavioral-modeling.md` | `role-permission-matrix.md`, `status-flow.md` (`locale-vi/`) | 0008 | prototype freeze + diagram coverage check | `docs/visuals/prototype/`, `docs/visuals/diagrams/*` |
| 7 | Story slicing | `scenario-taxonomy-playbook.md` (12 dims) | `story.md`, `high-risk-story/*` | 0004 | every REQ scenarised; tokens cited | `docs/stories/epics/EXX-name/US-NNN-*.md` |
| 8 | Build | — | (story.md § Implementation Guardrails) | 0007 | every commit cites REQ/SC token | code commits + `docs/TEST_MATRIX.md` rows |
| 9 | Code review | `code-review-scoring.md` (6-dim ≥ 7) | — | 0004 | any 0 auto-blocks merge | PR approval / block |
| 10 | QA + scenarios | `canonical-e2e-flow-playbook.md`, `e2e-qa-field-by-field-verify-with-report.md` | — | 0004 | every REQ → TC row in TEST_MATRIX | TC tokens in `docs/TEST_MATRIX.md` |
| 11 | UAT + signoff | — | `delivery-closure-story/` (`locale-vi/`) | 0007 | REQ coverage complete + visual matches prototype | `docs/stories/.../delivery-closure/*.md` |
| 12 | Release + client update | — | `release-note.md` (`locale-vi/`) | 0007 | pre-deploy + post-deploy smoke checklists pass | release note + client message sent |
| 13 | Handover + maintenance | — | `project-closure-story/` (`locale-vi/`), `maintenance-proposal.md` (`locale-vi/`) | 0007 | credentials access-verified + knowledge transfer logged | `docs/handover/*` + signed maintenance proposal |

## Per-Stage Detail

### 1. Lead

A potential client reaches out. Capture in any form (email, chat log, meeting notes). No artifact required yet — but any source doc shared by the client should be filed under `docs/discovery/YYYY-MM-DD-<slug>.{ext}` per `docs/discovery/README.md`.

### 2. Intake brief

**Purpose:** vendor-internal one-pager — should we take this project?

**Hook:** decide proceed-to-discovery / proceed-with-conditions / park / decline. If declining, send polite reply (template § 15) and stop.

**Reads:** `docs/discovery/*.md` (raw client inputs). **Writes:** `docs/intake/YYYY-MM-DD-intake-brief.md`.

### 3. Discovery

Two sub-steps. 3.A surfaces what the client said; 3.B structures what it means.

#### 3.A — Discovery interview

**Purpose:** structured conversation. 5 personas (End User / BA / QA / Developer / Operator) × 3 modes (Challenge / Guided / Explore).

**Time-box:** 60-90 min spec intake; 20-30 min change request.

**Reads:** intake brief + raw inputs. **Writes:** `docs/intake/YYYY-MM-DD-discovery-summary.md` (REQ list, decisions log, open questions).

#### 3.B — Gap analysis

**Purpose:** BA 4-step technique. Compare As-Is vs To-Be, structure the gaps, propose solutions with MoSCoW priority. Anchors SOW § 4 in-scope.

**Per-tier:** tiny skip; normal required when client has existing systems; high-risk required + stakeholder validation round.

**Skip when:** greenfield (no As-Is) or pure refactor (technical, document in decision).

**Reads:** discovery summary + intake brief + raw inputs. **Writes:** `docs/intake/YYYY-MM-DD-gap-analysis.md` with To-Be / As-Is / Gap (6 categories) / Plan of Action (MoSCoW).

**Hook:** vendor draft → client review round → freeze before SOW § 4.

### 4. Proposal & SOW

**Purpose:** priced commercial proposal.

**Critical sections:** § 4 in-scope (Must + selected Should from gap analysis Plan of Action), § 5 out-of-scope (Could + Won't + reason), § 7 milestones, § 8 payment schedule, § 9 change-request policy, § 10 acceptance conditions.

**Hook:** signed SOW + deposit before ANY code is written.

**Reads:** gap analysis Plan of Action. **Writes:** SOW (`locale-vi/` for VN clients).

### 5. Spec + Design intake

**Purpose:** derive harness artifacts from the aggregate "spec".

**Important:** there is no special `SPEC.md` file. The "spec" feeding this stage is the **aggregate** of:

- All raw input artifacts under `docs/discovery/` (client-provided spec, brainstorm notes, meeting transcripts, mockups, sample data) — see `docs/decisions/0009-discovery-input-folder-convention.md`.
- Vendor-produced intake artifacts under `docs/intake/` (intake-brief from stage 2, discovery-summary from stage 3.A, gap-analysis from stage 3.B if applicable).
- The signed SOW (`proposal-sow.md`) from stage 4.

**Hook:** Spec Approval Gate (`docs/FEATURE_INTAKE.md` § Spec Approval Gate). Phase 1 read+restate → human approves → Phase 2 derive.

**Output of Phase 1:** `docs/intake/YYYY-MM-DD-spec-intake.md` using `docs/templates/spec-intake.md`. Phase 2 then derives `docs/product/*`, `docs/design-guidelines.md`, and the decisions below.

**UI projects also:** Style Intake (5 sources) per `ui-design-system-contract.md` → `docs/decisions/YYYY-MM-DD-design-direction.md` → `docs/design-guidelines.md`.

**High-risk also:** `docs/decisions/NNNN-stack-selection.md` per `docs/ARCHITECTURE.md` § Discovery Before Shape. Use `docs/templates/decisions/stack-selection.md` as the question-shape.

**Reads:** `docs/discovery/*`, `docs/intake/*`, SOW. **Writes:** `docs/intake/YYYY-MM-DD-spec-intake.md`, then on Phase 2 approval → `docs/product/*`, `docs/design-guidelines.md`, decisions.

### 6. Visual & Behavioral Modeling

**Purpose:** prototype + behavioral diagrams BEFORE story slicing. Triple-use: client review + AI code handoff + UAT pass criterion.

**Sub-steps:**
- A. Design system check (confirm `docs/design-guidelines.md` from stage 5 covers prototype).
- B. Interactive prototype — Claude Design (https://claude.ai/design) primary; Stitch / Artifacts / v0.dev / pencil.dev fallbacks. → `docs/visuals/prototype/`.
- C. Business diagrams — sitemap, user flow, business workflow, ERD draft, Role-Permission Matrix, Status Flow per stateful entity. → `docs/visuals/diagrams/*`.

**Per-tier:** tiny skip; normal A + sitemap + 1 user flow + 1 prototype screen; high-risk all sub-steps required.

**Hook:** prototype frozen + diagrams frozen + RPM/Status Flow coverage checks before stage 7.

### 7. Story slicing

**Purpose:** cut product surface into story-sized work.

**Tokens:** every REQ becomes `US-NNN.REQ-MMM`; every scenario becomes `US-NNN.SC-MMM`.

**Scenario decomposition:** for each REQ, run `scenario-taxonomy-playbook.md` (12 dimensions). Forced skip-declarations.

**Inputs from stage 6:** RPM grid cells with REQ tokens become acceptance criteria; status-flow transitions become SC scenarios.

**Hook:** every REQ in story has at least one SC token decomposed (per per-tier rules).

**Reads:** product docs + design + visual artifacts. **Writes:** `docs/stories/epics/EXX-name/US-NNN-*.md` (high-risk uses `high-risk-story/` 4-file packet).

### 8. Build

**Purpose:** execute the story.

**Guardrails (story.md § Implementation Guardrails):**
- Stay inside scope; out-of-scope cleanup → new story or backlog.
- No architecture change without new decision.
- Don't delete code without proof (grep).
- Handle loading / empty / error states on UI.
- Input validation at boundary.
- Commit body explains change + cites at least one `US-NNN.REQ-MMM` or `US-NNN.SC-MMM`.

**Hook:** every commit cites at least one token.

### 9. Code review

**Purpose:** per-tier 6-dimension rubric.

**Rubric:** correctness 3 + security 2 + quality 2 + performance 1 + maintainability 1 + tests 1 = 10. Pass ≥ 7. Any dimension = 0 is auto-block.

**Per-tier:** tiny optional; normal 1 reviewer; high-risk 2 reviewers.

**Hook:** PR cannot merge if score < 7 OR any dimension = 0.

### 10. QA + scenarios

**Purpose:** prove the story behaves.

**Artifacts:** TC tokens in `docs/TEST_MATRIX.md` citing `US-NNN.SC-MMM` rows. Canonical E2E tests per `canonical-e2e-flow-playbook.md` (one journey per file, ≤ 8 assertions, cite TC token).

**Bug-for-tutorial flow:** `e2e-qa-field-by-field-verify-with-report.md` when same artifact serves user-guide demo.

**Hook:** every REQ cited in story has at least one TC row before UAT.

### 11. UAT + signoff

**Purpose:** client-facing acceptance gate.

**Artifacts:**
- `delivery-closure-story/overview.md` — wrapper.
- `01-uat-plan.md` — TC table ≤ 40 cases; each cites SC token.
- `02-signoff.md` — REQ coverage + exclusions + conditions.
- `03-client-update.md` — message sent.

**Visual gate:** live product matches frozen stage-6 prototype. Drift logged in change-request or bug list.

**Hook:** every `US-NNN.REQ-MMM` either passed or explicitly excluded with decision link.

### 12. Release + client update

**Purpose:** production deploy + structured client communication.

**Sub-checklists in template:**
- § 7 pre-deploy (test pass, DB backup, feature flags, env vars, third-party notify, rollback tested, on-call available).
- § 8 post-deploy smoke (homepage, login, core action, error-rate, alerts, payment, background jobs, logs).
- § 9 rollback plan + when to trigger.
- § 11 client-update message.

**Hook:** every released REQ token appears in release note; deferred REQs link to follow-up story.

### 13. Handover + maintenance

**Purpose:** end-of-project ownership change + recurring revenue offer.

**Artifacts:**
- `project-closure-story/overview.md` — wrapper.
- `01-handover-docs.md` — read-this-order index.
- `02-credentials-handover.md` — vault-pointer checklist (no raw secrets).
- `03-knowledge-transfer.md` — sessions log.
- Stage-6 artifacts also ship: prototype URL + diagrams + frozen RPM + status flows.

**Then:** send `maintenance-proposal.md` (Basic / Standard / Premium tiers).

**Hook:** every credential row access-verified by incoming owner; knowledge-transfer sessions logged.

## Always-On Layer

### Change Request

Independent of stage. Any client request after SOW signing enters the log.

- **Template:** `docs/templates/change-request-log.md` (`locale-vi/`).
- **Classification:** bug / change-request / new-feature / ux-improvement / clarification.
- **Reply templates:** 5 included (in-scope bug, out-of-scope quote, phase 2 defer, clarification, S1 incident).
- **Hook:** every CR closed when status = `done | deferred | rejected` AND reply sent.

### Audit Trail

- Every signed-off REQ has at least one TC row in `TEST_MATRIX.md`.
- Every deviation from SOW lives in `change-request-log.md`.
- Every architecture change has a `docs/decisions/NNNN-*.md`.
- Every multi-task session (3+ commits OR spans multiple intake items) ends with `session-retrospective.md` → `plans/reports/retro-<date>-<slug>.md`.

## Folder Reference

```text
docs/
├── discovery/          # Raw inputs (immutable, append-only, from client)
│   └── README.md
├── intake/             # Vendor briefs (transitional, frozen at downstream creation)
│   └── README.md
├── product/            # Current product contract (derived from intake)
├── stories/            # Story packets + epics
├── decisions/          # Numbered ADRs (NNNN-*.md)
├── playbooks/          # Reusable recipes (lifecycle: experimental | verified | deprecated)
├── templates/          # Shape-only scaffolds
│   └── locale-vi/      # Vietnamese forks (client-facing surface only)
├── visuals/            # Stage 6 outputs (project-specific, NOT shipped in installer)
│   ├── prototype/
│   └── diagrams/
└── handover/           # Stage 13 outputs (project-specific)
```

## Token Chain

End-to-end traceability across the workflow:

```text
Business problem (stage 2)
    ↓ analysed by gap analysis (stage 3.B)
GAP-NNN (local to gap-analysis brief)
    ↓ feeds SOW § 4 (stage 4) + story slicing (stage 7)
US-NNN          (story ID)
US-NNN.REQ-MMM  (requirement inside story)
    ↓ scenarised by scenario-taxonomy (12 dims, stage 7)
US-NNN.SC-MMM   (scenario / edge case)
    ↓ proven by QA (stage 10)
US-NNN.TC-MMM   (test case)
    ↓ row in
docs/TEST_MATRIX.md
    ↓ validated at
UAT (stage 11) — each TC cites SC token in Path column
    ↓ released in
release note (stage 12) — every released REQ appears
    ↓ handed over in
delivery handover (stage 13) — included in 01-handover-docs.md
```

Per-lane application:

- **Tiny:** tokens optional; inline narrative fine.
- **Normal:** required for any new REQ / SC the story introduces.
- **High-risk:** required everywhere — `execplan.md`, `design.md`, `validation.md` cite their tokens.

## Per-Tier Stage Matrix

Which stages run for which lane? Tiny / Normal / High-risk per `docs/FEATURE_INTAKE.md`.

| Stage | Tiny | Normal | High-Risk |
|---|---|---|---|
| 1 Lead | — | — | — |
| 2 Intake brief | optional | required | required |
| 3.A Discovery interview | optional | required | required |
| 3.B Gap analysis | skip | required if existing systems | required + stakeholder validation |
| 4 Proposal & SOW | skip if no commercial | required | required |
| 5 Spec + Design intake | optional | required | required + stack-selection decision |
| 6 Visual & Behavioral Modeling | skip | partial (sitemap + 1 user flow + 1 prototype screen) | full (all 3 sub-steps + RPM + Status Flow per entity) |
| 7 Story slicing | story.md | story.md + scenario-taxonomy | high-risk-story/ packet + full scenario-taxonomy |
| 8 Build | inline narrative | full guardrails | full guardrails + decision required for arch change |
| 9 Code review | optional | 1 reviewer | 2 reviewers |
| 10 QA + scenarios | inline | TEST_MATRIX rows required | TEST_MATRIX + canonical-e2e-flow |
| 11 UAT + signoff | optional | required | required + visual conformance gate |
| 12 Release + client update | release note optional | release note + smoke required | release note + smoke + rollback test |
| 13 Handover + maintenance | minimal | full handover | full handover + maintenance proposal |

## Locale Forks (Vietnamese)

Client-facing surface only. Internal templates stay English. Per `docs/playbooks/bilingual-delivery-template-pattern.md`.

```text
docs/templates/locale-vi/
├── client-intake-brief.md          # stage 2
├── gap-analysis.md                 # stage 3.B
├── proposal-sow.md                 # stage 4
├── change-request-log.md           # always-on
├── release-note.md                 # stage 12
├── maintenance-proposal.md         # stage 13
├── role-permission-matrix.md       # stage 6
├── status-flow.md                  # stage 6
├── delivery-closure-story/
│   ├── 01-uat-plan.md              # stage 11
│   ├── 02-signoff.md               # stage 11
│   └── 03-client-update.md         # stage 11
└── project-closure-story/
    └── 01-handover-docs.md         # stage 13
```

Files NOT forked (stay English): `story.md`, `decision.md`, `spec-intake.md`, `validation-report.md`, `high-risk-story/*`, `delivery-closure-story/overview.md`, `project-closure-story/{overview,02-credentials-handover,03-knowledge-transfer}.md`.

## Decision Audit Map

Decisions authorising the workflow's shape:

| Decision | Authorised |
|---|---|
| 0001 | Harness-first development (no app code before harness) |
| 0002 | Post-spec product lifecycle (product/stories/decisions as living surface) |
| 0003 | Generic spec-intake (no project-specific SPEC in v0) |
| 0004 | Adopt ClaudeKit Custom patterns (traceability tokens + 6-dim review + bilingual + composition + production-readiness) |
| 0005 | Roadmap execution direction + promotion rule (2 projects OR 1 project × 3+) |
| 0006 | Session retrospective mechanic (Task Loop step 9) |
| 0007 | Solo-dev commercial wrapper (5 templates + meta-playbook + VN starter) |
| 0008 | Stage 6 Visual & Behavioral Modeling insertion |
| 0009 | Discovery input folder convention (`docs/discovery/` + naming) |
| 0010 | Stage 3.B Gap Analysis (BA technique) insertion |
| 0011 | Bootstrap mode for `install-harness.sh` (`--bootstrap` + `--spec`) |

## Quick Links

- **Authority:** `docs/playbooks/solo-dev-client-delivery.md`
- **Operating model:** `docs/HARNESS.md`
- **Feature intake:** `docs/FEATURE_INTAKE.md`
- **Architecture rules:** `docs/ARCHITECTURE.md`
- **Test matrix:** `docs/TEST_MATRIX.md`
- **Token format:** `docs/HARNESS.md` § Traceability Tokens
- **Playbook lifecycle:** `docs/HARNESS.md` § Playbook Lifecycle
- **Discovery folder:** `docs/discovery/README.md`
- **Intake folder:** `docs/intake/README.md`
- **Bilingual fork pattern:** `docs/playbooks/bilingual-delivery-template-pattern.md`
- **Backlog:** `docs/HARNESS_BACKLOG.md`

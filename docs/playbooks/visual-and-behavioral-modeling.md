# Visual & Behavioral Modeling Playbook

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Stage 6 of `docs/playbooks/solo-dev-client-delivery.md`. Runs after design tokens are set (stage 5) and before story slicing (stage 7). Produces three artifact families that serve TRIPLE duty: client review surface + AI code-generation handoff + UAT reference baseline.

## Why This Stage Exists

Without it:

- Clients give cosmetic feedback on a clickable demo at UAT (late, expensive).
- AI code generation drifts because it has no visual contract.
- Permission and state-machine bugs surface in production audit logs.
- Disputes at UAT escalate because "what we agreed to build" lives only in prose.

With it:

- A single visual artifact is reviewed BEFORE code, after which "matches the agreed prototype" is the UAT pass criterion.
- AI code generation has a pixel-anchored target (Claude Design handoff, Stitch HTML export, v0.dev component dump).
- Permission + state holes show up as gaps in the matrix / status-flow table, not as security incidents.

## When To Run

- For any project where the client is non-tech AND will be asked to accept the product at UAT.
- For any project touching authorization (roles, permissions) OR stateful entities (orders, applications, tickets).
- For any project where the AI coding tool's output quality depends on a visual reference.

Skip when:

- Internal tool with one role and no state machines.
- Pure refactor or migration — no new product surface.
- Client is technically literate AND reads PRD-style spec without visual loss.

## Output Folder

All artifacts land under `docs/visuals/` in the project repo. Sub-folders:

```text
docs/visuals/
├── design-system/           # pointer to docs/design-guidelines.md if used
├── prototype/
│   ├── README.md            # tool used, claude.ai/design link, freeze date
│   ├── screens/             # exported HTML / PNG per screen
│   └── flows/               # interactive flow walkthroughs (mp4 / gif / link)
└── diagrams/
    ├── sitemap.md
    ├── user-flow-<flow-name>.md
    ├── business-workflow-<workflow-name>.md
    ├── erd-draft.md
    ├── role-permission-matrix.md
    └── status-flow-<entity>.md
```

## Sub-Step A — Design System Check

Confirm the design system contract from stage 5 exists and is current. This is a CHECK, not a rebuild.

Required: `docs/design-guidelines.md` exists and was produced via `docs/playbooks/ui-design-system-contract.md` § Style Intake.

Gate before sub-step B: § 3 Component Coverage Matrix in the contract covers every component the prototype will use. Missing components → either stub the row (TODO) or generate the component before prototyping the screens that need it.

If the contract does NOT exist, stop and run `docs/playbooks/ui-design-system-contract.md` first. Skipping this gate guarantees prototype drift.

## Sub-Step B — Interactive Prototype

Generate a clickable prototype that LOOKS LIKE the final product. The prototype is the client's mental model anchor.

### Tool Ladder

Pick the highest tool the project has access to. All tools must accept the design tokens from sub-step A as input.

| Rank | Tool | Notes |
| --- | --- | --- |
| 1 | **Claude Design** — https://claude.ai/design | Anthropic's design tool. Has native "handoff to Claude Code" — output is directly consumable by the build stage. Reference design tokens via paste or link. May require account access; if unavailable, fall back to rank 2. |
| 2 | **Google Stitch** — `/stitch` skill | AI design generation with HTML/Tailwind export. Strong layout suggestions; manual token application. |
| 3 | **Anthropic Claude Artifacts** | claude.ai chat with React artifact. Good for single-component prototypes; clunky for whole-app flows. |
| 4 | **v0.dev** (Vercel) | Strong React/Tailwind output. Less faithful to custom tokens unless prompted carefully. |
| 5 | **pencil.dev / penpot / Figma + AI plugins** | Designer-driven; slower but highest visual fidelity. Manual code handoff. |
| 6 | **HTML/Tailwind hand-write via /frontend-design** | Last resort. Slowest but fully controlled. |

Rank 1-2 are recommended for solo-dev projects. Higher ranks generate faster, leaving more time for client iteration. Document the chosen tool + URL + version in `docs/visuals/prototype/README.md`.

### Inputs

- Design tokens from sub-step A (`docs/design-guidelines.md`).
- Sitemap / screen list draft (can start empty; generate iteratively).
- Sample data (typical record, edge cases) — paste so empty/error states render meaningfully.

### Outputs

The harness ships the prototype folder skeleton ready to fill:

```text
docs/visuals/prototype/
├── README.md      # pre-filled template — replace placeholders, do not recreate
├── screens/       # one HTML or PNG export per screen lands here
└── flows/         # one recording or live-URL stub per primary journey
```

- Fill `docs/visuals/prototype/README.md` (tool, URL, version, freeze date, screen coverage table, flow coverage table, known limitations). Do **NOT** delete the placeholder rows before filling — overwrite them.
- Drop one HTML or PNG export per screen into `docs/visuals/prototype/screens/`.
- Drop one flow walkthrough (recording or live URL stub) per primary user journey into `docs/visuals/prototype/flows/`.

### Client Review Loop

1. Vendor shares prototype URL or screen exports with client.
2. Client reviews each primary flow (target: ≤ 30 minutes per flow).
3. Vendor logs feedback in `docs/visuals/prototype/feedback-YYYY-MM-DD.md` (one file per round).
4. Vendor regenerates affected screens; bumps freeze date.
5. Repeat until client signs off OR vendor + client agree on what changes ship in phase 2.

Time-box: 2 review rounds maximum before freeze. Beyond 2, scope is the problem — escalate via change-request log.

### Freeze Gate

Prototype is frozen when:

- [ ] Client confirms in writing (`docs/visuals/prototype/feedback-final.md` with timestamp).
- [ ] Every screen has at least 1 sample-data export AND 1 empty/error state export.
- [ ] Tool version + URL captured in README.
- [ ] Prototype URL is preserved (account-private or vendor-hosted — must survive past UAT).

### Triple-Use Rule

The frozen prototype serves three downstream consumers:

1. **Client at UAT** — "does the live product match the frozen prototype?" is the visual pass criterion (`docs/templates/delivery-closure-story/01-uat-plan.md`).
2. **AI code generation at stage 7-8** — the build stage cites prototype screens as the target for each component. Claude Design "handoff to Claude Code" is the integrated form of this; for other tools, the dev pastes screenshots into the implementation prompt.
3. **Final handover at stage 13** — the prototype is part of the delivered artifact set (`docs/templates/project-closure-story/01-handover-docs.md`).

Do not regenerate the prototype post-freeze. Any change after freeze enters `docs/templates/change-request-log.md`.

## Sub-Step C — Business Diagrams

Five diagrams. Each one catches a different class of defect.

### C.1 — Sitemap

What: a flat list of every page / screen the product will have.
Where: `docs/visuals/diagrams/sitemap.md`.
Shape: indented bullet list grouped by user role (guest, customer, staff, admin).
Catches: "we forgot the staff dashboard" before story slicing.

### C.2 — User Flow (per primary journey)

What: step-by-step path a user takes to complete one job-to-be-done. One file per major flow (signup, checkout, refund, etc.).
Where: `docs/visuals/diagrams/user-flow-<flow-name>.md`.
Shape: Mermaid flowchart + numbered step list.
Catches: "where does the user go after the success page?" before AI generates a dead-end.

### C.3 — Business Workflow

What: cross-role process model (who hands off to whom) for any multi-role process.
Where: `docs/visuals/diagrams/business-workflow-<workflow-name>.md`.
Shape: Mermaid sequenceDiagram or swimlane (or BPMN-lite ASCII).
Catches: "staff has no way to escalate to admin" before fulfillment stalls.

### C.4 — ERD Draft

What: entity-relationship diagram, draft level (no every-field detail).
Where: `docs/visuals/diagrams/erd-draft.md`.
Shape: Mermaid erDiagram. Field-level schema lives in the eventual stack decision OR migration; this is the contract for which entities + cardinalities.
Catches: "we modeled order as belongs-to-user but the spec needs guest orders" before migrations are written.

Linkage: when the stack-selection decision lands (`docs/ARCHITECTURE.md` § Discovery Before Shape), this ERD is the input for the schema decision.

### C.5 — Role-Permission Matrix

What: who-can-do-what grid.
Where: `docs/visuals/diagrams/role-permission-matrix.md` from `docs/templates/role-permission-matrix.md`.
Shape: roles × resources × CRUD grid with conditional codes + REQ token citations.
Catches: "staff was supposed to be able to refund but no story granted refund permission" before audit-log incidents.

### C.6 — Status Flow (per stateful entity)

What: state machine per entity that has workflow states.
Where: `docs/visuals/diagrams/status-flow-<entity>.md` from `docs/templates/status-flow.md`. One file per entity.
Shape: Mermaid stateDiagram-v2 + transition table with role / pre-condition / side-effect columns.
Catches: "user got stuck in 'in-review' because no transition leads back to 'pending'" before production tickets pile up.

#### Strict Rule (high-risk lane)

For the high-risk lane, **every stateful entity MUST have a status-flow file**. Strict, no exceptions short of a `docs/decisions/NNNN-*.md` documenting the skip.

An entity is **stateful** when ANY of the following is true:

- The entity's row in the ERD has a `status`, `state`, `phase`, or similarly-named enum column.
- The entity has ≥ 2 distinct states that gate downstream behavior (visibility, permissions, side-effects).
- Different roles take different actions depending on which state the entity is in.
- The state of the entity is recorded in an audit log on transition.

Examples of stateful entities to cover (project-specific — pick from the ERD): `order`, `payment`, `subscription`, `user`, `kyc_application`, `support_ticket`, `vendor_application`, `invoice`, `refund`, `dispute`.

Examples that are NOT stateful (skip): purely-read entities (e.g. `country`, `currency`), join tables (`order_items`), append-only audit rows.

If unsure: write the file. The cost of a 30-minute status-flow doc is far below the cost of a production state-machine bug.

##### Coverage check before freeze

Before stage 6 freeze, run:

```text
For each entity in docs/visuals/diagrams/erd-draft.md:
  If entity has a `status` / `state` column OR ≥ 2 states OR is in the
  "stateful entity list" of the design intake:
    → docs/visuals/diagrams/status-flow-<entity>.md MUST exist.
    → File MUST be referenced from docs/stories/backlog.md or a story.
```

Surface any miss as a freeze blocker — stage 7 (Story slicing) cannot start until the gap is closed (file exists OR a decision doc records the explicit skip).

### Freeze Gate For Diagrams

Before stage 7 (Story slicing) begins:

- [ ] All 5 (or 6, including status flow) diagram files exist.
- [ ] Sitemap covers every prototype screen.
- [ ] Every primary user flow has a User Flow doc.
- [ ] ERD draft entities match Role-Permission Matrix resources.
- [ ] Role-Permission Matrix § Coverage Check passes.
- [ ] Status Flow § Coverage Check passes (for each stateful entity).

## Cross-Stage Hand-Off Rules

| Going INTO stage 6 | Required |
| --- | --- |
| from stage 5 | `docs/design-guidelines.md` exists; Component Coverage Matrix populated. |
| Going OUT OF stage 6 | Required |
| to stage 7 (Story slicing) | Prototype frozen; all 5-6 diagrams frozen; Role-Permission Matrix tokens cited. |
| to stage 10 (UAT) | Prototype URL still accessible; UAT plan cites prototype as visual pass criterion. |
| to stage 13 (Handover) | Prototype + diagrams ship as part of `01-handover-docs.md` § Maintenance Surfaces. |

## Anti-Patterns

- **Skipping when client is non-tech.** That is the exact case where this stage pays for itself. Do not skip.
- **Generating prototype before design tokens.** Drift is guaranteed. Run sub-step A first.
- **Letting iteration run > 2 rounds without freeze.** Either the scope is wrong or the client is using the prototype as a discovery surface. Escalate via change-request or re-open SOW § 4.
- **One huge diagram file.** Split per flow / per entity. File-level grep is the audit mechanism.
- **Diagram + prototype that disagree.** They are two views of one fact. When they disagree, the prototype wins for UI, the diagrams win for behavior. Reconcile within 1 working day; do not ship contradictions.
- **Treating these as one-time outputs.** They are living until UAT freeze. Update via the change-request flow.

## Per-Tier Application

| Lane | Application |
| --- | --- |
| Tiny | Skip whole stage. |
| Normal | Sub-step A + at least sitemap + user flow + 1 prototype screen for any client-visible surface. RPM + Status Flow optional. |
| High-risk | All sub-steps required. RPM + Status Flow **strict** — every stateful entity per § C.6 Strict Rule must have a file, or a decision documenting the skip. |

## Variant Section

(Append a Variant block here when this playbook fails or partially works. Do not delete the original shape.)

## Related

- `docs/playbooks/solo-dev-client-delivery.md` — caller (stage 6).
- `docs/playbooks/ui-design-system-contract.md` — sub-step A source.
- `docs/playbooks/mermaidjs-v11` (skill) — diagram rendering, if installed.
- `docs/templates/role-permission-matrix.md` — sub-step C.5.
- `docs/templates/status-flow.md` — sub-step C.6.
- `docs/templates/delivery-closure-story/01-uat-plan.md` — consumer at stage 10.
- `docs/templates/project-closure-story/01-handover-docs.md` — consumer at stage 13.
- `docs/decisions/0008-visual-behavioral-modeling-stage.md` — adoption decision.

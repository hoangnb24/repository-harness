# Harness Backlog

Use this file when an agent discovers a missing harness capability but should
not change the operating model immediately.

## Template

```md
## Missing Harness Capability

### Title

Short name.

### Discovered While

Task or story that exposed the gap.

### Current Pain

What was hard, repeated, ambiguous, or unsafe?

### Suggested Improvement

What should be added or changed?

### Demand Evidence

Projects, dates, or recurrences that justify (or do not yet justify)
promotion. Update each time a new hit is observed.

### Risk

Tiny, normal, or high-risk.

### Status

proposed | accepted | implemented | rejected
```

## Promotion Rule

Codified by `docs/decisions/0005-roadmap-execution-direction.md` § 5.

A `proposed` item promotes to a decision (and optionally a plan) when
EITHER:

- **Cross-project signal:** 2 distinct projects independently ask for the
  same capability. The portability mandate justifies a portable artifact.
- **Sustained-pain signal:** 1 project hits the gap 3+ times. Recurrence
  proves the friction is not a one-off.

Promotion mechanic:

1. Update the item's `Demand Evidence` field with the qualifying hits.
2. Move status from `proposed` to `accepted`.
3. Write a decision document (`docs/decisions/NNNN-*.md`) referencing this
   backlog entry.
4. If implementation work is non-trivial, also create a plan directory.

Items that sit at `proposed` for 12+ months with no Demand Evidence may
be marked `rejected` with a one-line rationale.

Related: `docs/HARNESS.md` § Playbook Lifecycle uses the same demand
threshold (1 successful real use OR 2 partial uses) to promote individual
playbooks from `experimental` to `verified`. Backlog items become
playbooks; playbooks then mature through the lifecycle states.

## Items

## Missing Harness Capability

### Title

Dynamic file discovery for `install-harness.sh`

### Discovered While

Auditing the install script after a user asked which install method to
prefer for greenfield (2026-05-17). Found three newly-shipped playbooks
(`e2e-recording-user-guide-quality.md`, `e2e-qa-field-by-field-verify-with-report.md`,
`ui-design-system-contract.md`) silently absent from the hardcoded
`HARNESS_FILES` list — anyone who curl-installed after 2026-05-16 was
missing them. Patched the list immediately, but the root cause is the
hardcoded approach.

### Current Pain

`scripts/install-harness.sh` ships files via a hardcoded heredoc list
at lines 357-387. Every new playbook, template, or doc requires manual
list maintenance. No CI guard detects drift between repo state and
shipped state. Authors of new files have no signal that their work
won't reach installer users until someone notices the gap weeks later.

### Suggested Improvement

Pick one of three approaches:

1. **Tarball download** — fetch a tarball of the repo at `main`, extract
   only the shipped paths (`AGENTS.md`, `docs/`, `scripts/`). Simpler,
   one network call, naturally picks up new files.
2. **GitHub API directory listing** — query `/repos/.../contents/docs`
   recursively, copy matching paths. More requests but no shell-list
   maintenance.
3. **Hardcoded list with CI guard** — keep current approach but add a
   CI step that diffs the heredoc against `git ls-files` filtered to
   shipped paths and fails on drift.

Option 1 is simplest to implement; option 3 is cheapest to ship today.

### Risk

Normal — install correctness is high-leverage but the fix is contained
to one script.

### Status

proposed

## Missing Harness Capability

### Title

Bootstrap mode for `install-harness.sh` (accepted)

### Discovered While

Documenting greenfield workflow from `SPEC.md` (2026-05-17).

### Current Pain

`install-harness.sh` assumes the target directory is an existing project
(prompts to merge / override / stop on existing files). Greenfield
projects starting from a written spec require manual steps:
`git clone` the harness, `rm -rf .git && git init`, manually place
`SPEC.md`. The README's "Greenfield Bootstrap" section now documents
this manual path, but it should be a single command.

### Suggested Improvement

Add a `--bootstrap` flag that:
1. Initializes a fresh git repo in the target directory.
2. Copies all harness files unconditionally (no merge prompts).
3. Optionally accepts `--spec <path>` to copy the user's spec to
   `docs/discovery/YYYY-MM-DD-initial-spec.<ext>` in one step (per
   decision 0009, not `./SPEC.md` as originally proposed).
4. Prints the "next prompt" (the Claude Code prompt that runs Phase 1
   intake) so the user can copy-paste straight in.

### Demand Evidence

- 2026-05-17 — Pre-flight audit for first real paid client project
  (`plans/reports/review-260517-1728-pre-flight-workflow-audit.md` § C3)
  flagged as Critical fix before opening the project. Single-project
  sustained-pain trigger per decision 0005 § 5.

### Risk

Normal.

### Status

accepted (implemented 2026-05-17 — see `docs/decisions/0011-bootstrap-installer-mode.md`)

## Missing Harness Capability

### Title

Standard file-naming convention for discovery artifacts (B1)

### Discovered While

ClaudeKit Custom scan 2026-05-17 (`plans/reports/xia-260517-1130-claudekit-custom-skill-scan.md`,
Tier B item ck:intake-file).

### Current Pain

Harness intake currently does not prescribe how raw discovery artifacts
(meeting notes, BPMNs, screenshots, sample data) should be named or
filed. ck:intake-file uses `YYYY-MM-DD-{descriptive-kebab-slug}.{ext}`
inside a fixed `discovery-input/{01-business-context, ...}/` folder
structure. Adopting that wholesale is too rigid for harness's
"grows from friction" stance, but the date-prefix file-naming idea is
portable.

### Suggested Improvement

Add a one-page playbook documenting a recommended file-name convention
for discovery artifacts (`YYYY-MM-DD-{kebab-slug}.{ext}`) and a default
folder choice (`docs/discovery/`). Leave folder structure unprescribed;
agents file by topic when topic clusters emerge.

### Demand Evidence

- 2026-05-17 — Solo-dev VN e-commerce project hit the gap immediately:
  user dropped source doc at repo root → agent mis-filed to
  `plans/reports/` → user redirected with explicit requirement "folder
  for inputs like SPEC.md but for many artifacts (meeting notes,
  screenshots, change request raw)". Single-session 2 hits.

### Risk

Tiny.

### Status

accepted (implemented 2026-05-17 — see `docs/decisions/0009-discovery-input-folder-convention.md` and `docs/discovery/README.md`)

## Missing Harness Capability

### Title

Persona discovery process playbook (B2)

### Discovered While

ClaudeKit Custom scan 2026-05-17 (Tier B item ck:persona).

### Current Pain

Harness has no canonical way to capture stakeholder personas before
story work begins. Plan C discovery interview playbook (when shipped)
implicitly covers persona discovery via the End User / BA / QA /
Developer / Operator framework, but a dedicated lightweight persona
artifact is missing.

### Suggested Improvement

Optional playbook that turns persona discovery into a small structured
output (1-page persona summary per persona: role, primary motivations,
failure modes, evidence basis). NOT a full UX research deliverable.
Re-evaluate after Plan C ships — discovery interview output may already
cover this and make the playbook redundant.

### Demand Evidence

None. `docs/playbooks/discovery-interview-playbook.md` shipped with
5-persona × 3-mode coverage; no project has hit the "need a separate
persona artifact" gap.

### Risk

Tiny.

### Status

rejected (2026-05-17 — pre-flight audit: discovery-interview-playbook covers it; revisit only if 2+ distinct projects hit a real gap)

## Missing Harness Capability

### Title

Brand-direction discovery process (B3)

### Discovered While

ClaudeKit Custom scan 2026-05-17 (Tier B item ck:brand-guidelines).

### Current Pain

`docs/playbooks/ui-design-system-contract.md` § Style Intake already
covers the brand-direction discovery surface for UI work, but the
broader brand voice / tone / copy rules questions for non-UI
deliverables (client comms, signoff doc tone, hypercare comms) have no
documented discovery shape.

### Suggested Improvement

Either amend the UI design system contract playbook with a Style Intake
variant that covers non-UI surfaces, OR ship a separate small playbook
specifically for comms-tone discovery. Pick after first real project
exposes which need is sharper.

### Demand Evidence

None.

### Risk

Tiny.

### Status

rejected (2026-05-17 — pre-flight audit: zero demand evidence; reopen if 2+ projects request)

## Missing Harness Capability

### Title

Extract `/ck:*` recommendations in existing playbooks into clearly-optional Tooling Hints (B6)

### Discovered While

Independence Principle audit 2026-05-17 (decision 0005 closure +
checking claudekit-custom coupling across all shipped harness surface).

### Current Pain

Five pre-existing playbooks inline `/ck:*` skill recommendations in
their core logic body, making it ambiguous whether the skill is a
required tool or optional convenience:

- `headless-browser-blank-screenshot.md` — refs `/ck:agent-browser`,
  `/ck:chrome-devtools`, `/ck:web-testing`, `/ck:ai-multimodal`.
- `landing-page-saas-ai-noti-style.md` — refs `/ck:frontend-design`,
  `/ck:ui-styling`, `/ck:ui-ux-pro-max`, `/ck:web-design-guidelines`.
- `ui-design-system-contract.md` — refs `/ck:ai-multimodal`,
  `/ck:stitch`, `/ck:ui-ux-pro-max`, `/ck:design`, `/ck:frontend-design`,
  `/ck:ui-styling`, `/ck:web-design-guidelines`, and
  `/ck:ck-extract-design-system` (the only claudekit-custom ref in
  shipped harness).
- `e2e-qa-field-by-field-verify-with-report.md` — refs `/ck:web-testing`,
  `/ck:ai-multimodal`, `/ck:chrome-devtools`.
- `e2e-recording-user-guide-quality.md` — refs `/ck:web-testing`,
  `/ck:ai-multimodal`, `/ck:chrome-devtools`, `/ck:test`.

Per `docs/HARNESS.md` § Independence Principle, recommendations are
allowed but core logic must be tool-independent and recommendations
must be clearly optional. Current inline placement violates the
"clearly optional" half of that contract.

### Suggested Improvement

For each affected playbook:

1. Move all `/ck:*` references out of body sections into a `§ Tooling
   Hints` appendix at the bottom (or extend the existing
   `§ Related Tools And Skills` section if present).
2. Tag each hint as "Optional — convenience wrapper" with the fallback:
   - `/ck:web-testing` → use Playwright directly.
   - `/ck:ai-multimodal` → call Gemini API or vision model directly.
   - `/ck:agent-browser` / `/ck:chrome-devtools` → use Puppeteer or
     Playwright directly.
   - `/ck:stitch` / `/ck:frontend-design` / `/ck:ui-styling` /
     `/ck:ui-ux-pro-max` / `/ck:web-design-guidelines` / `/ck:design` →
     manual design work or the underlying upstream tools.
   - `/ck:ck-extract-design-system` → manual design token extraction.
   - `/ck:test` → invoke test framework directly.
3. Ensure the playbook body reads sensibly without ever mentioning a
   `/ck:*` skill — the appendix is enrichment, the body is logic.

### Demand Evidence

None — flagged by Independence Principle audit; no project has hit a
real coupling failure yet. Hold at `proposed` until promotion threshold
is met (2 distinct projects affected, or 1 project hit 3+ times trying
to run the playbook without ClaudeKit installed).

### Risk

Tiny. Docs reorg only. No logic change to any playbook.

### Status

proposed

## Missing Harness Capability

### Title

Multi-image / multi-artifact analysis pattern (B5)

### Discovered While

ClaudeKit Custom scan 2026-05-17 (Tier B item ck:extract-design-system).

### Current Pain

When a discovery batch ships multiple related artifacts (screenshots of
existing system, sample data files, BPMN diagrams), there is no
documented playbook for systematically analysing them as a set rather
than one-by-one. ck:extract-design-system shows one specialised version
(reverse-engineer design tokens from screenshots) — the general pattern
is portable.

### Suggested Improvement

Playbook describing how an agent should analyse a multi-artifact
discovery batch: inventory the set, classify each artifact, find
contradictions across artifacts, surface the consolidated finding plus
the per-artifact notes.

### Demand Evidence

None.

### Risk

Tiny.

### Status

proposed

## Missing Harness Capability

### Title

Commercial wrapper for solo-dev client delivery (5 templates + meta-playbook)

### Discovered While

Compare-mode audit (`plans/reports/xia-260517-1538-solo-dev-vibecode-vs-harness.md`)
against an AI-suggested 15-stage solo-dev workflow on 2026-05-17. Confirmed by
a real VN e-commerce / dashboard project starting the same week that requires
end-to-end commercial delivery with the harness.

### Current Pain

Harness shipped strong internal-facing artifacts (intake, story templates,
scenario taxonomy, code-review scoring, closure templates, handover) but had
no commercial wrapper: no SOW / proposal, no maintenance offer, no
release-note + deployment-checklist + rollback, no client-facing
change-request log, no pre-discovery client-intake brief that gates the
accept / decline decision.

Solo dev running a paid client project end-to-end through the harness would
have to invent these artifacts under client deadline pressure, with no review
cycle. Scope-creep risk and payment risk are both bounded by these missing
templates.

### Suggested Improvement

Ship five new English commercial templates plus one meta-playbook plus a
`locale-vi/` starter for client-facing surface (existing closure templates
included). Internal templates stay English-only. Add § Implementation
Guardrails to `docs/templates/story.md`. New `docs/templates/README.md`
index. Documented in `docs/decisions/0007-solo-dev-client-delivery-templates.md`.

### Demand Evidence

- 2026-05-17 — `plans/reports/xia-260517-1538-solo-dev-vibecode-vs-harness.md`
  audit identified the gap.
- 2026-05-17 — solo-dev VN e-commerce / dashboard project queued, will run
  through every stage in the next 4-6 weeks. Single project but 12-stage
  end-to-end exposure — equivalent in spirit to 3+ separate hits per
  `0005-roadmap-execution-direction.md` § 5 sustained-pain rule.

### Risk

Normal — five templates + one meta-playbook + one decision + index updates.
Mitigated by: meta-playbook is pointers-only (no duplication), templates
are shape-only (no project-specific content), VN fork is starter not
mandate.

### Status

accepted (implemented 2026-05-17 — see `docs/decisions/0007-solo-dev-client-delivery-templates.md`)

## Missing Harness Capability

### Title

Visual & behavioral modeling stage for solo-dev client delivery

### Discovered While

Same-day follow-up to commit 22c0529 (decision 0007). Real solo-dev VN
e-commerce / dashboard project (2026-05-17) surfaced the structural gap
between stage 5 (Spec + Design intake) and stage 6 (Story slicing): there
was no explicit phase for producing the visual + behavioral artifacts
that anchor non-tech client review, AI code-generation handoff, and UAT
pass criteria.

### Current Pain

Without a dedicated stage:
- Client gives cosmetic feedback on a clickable demo only at UAT — late
  and expensive.
- AI code generation drifts because it has no visual contract.
- Permission and state-machine bugs surface in production audit logs
  instead of in design-time matrix / status-flow tables.
- Scope disputes at UAT escalate because "what we agreed to build" lives
  only in prose.

Existing `ui-design-system-contract.md` covers design tokens but not
interactive prototypes. No template for Role-Permission Matrix or
Status Flow — two of the highest-leverage behavioral artifacts.

### Suggested Improvement

Insert new stage 6 "Visual & Behavioral Modeling" into the meta-playbook
(renumber 6-12 → 7-13). Ship:
- `docs/playbooks/visual-and-behavioral-modeling.md` (3 sub-steps).
- `docs/templates/role-permission-matrix.md` + locale-vi fork.
- `docs/templates/status-flow.md` + locale-vi fork.
- Decision 0008.
- Index updates + install heredoc sync.

Tool ladder: Claude Design (https://claude.ai/design) primary, with
Stitch / Artifacts / v0.dev / pencil.dev / hand-write fallbacks. Output
folder `docs/visuals/`.

### Demand Evidence

- 2026-05-17 — user surfaced gap based on prior client-work pain.
- 2026-05-17 — same VN e-commerce project cited in decision 0007 will
  exercise this stage in next 4-6 weeks. Same-project second-hit on the
  commercial-wrapper area within hours of 0007 implementation.

### Risk

Normal — 5 new files + meta-playbook edit + heredoc sync + decision.
Mitigated by: playbook composes existing pieces (no duplication);
templates are shape-only; tool ladder avoids hard dependency on
Claude Design availability.

### Status

accepted (implemented 2026-05-17 — see `docs/decisions/0008-visual-behavioral-modeling-stage.md`)

## Missing Harness Capability

### Title

BA Gap Analysis (As-Is vs To-Be) stage for solo-dev client delivery

### Discovered While

Same-day follow-up to decisions 0007-0009. Solo-dev VN e-commerce / dashboard
project preparing to start; user flagged that the meta-playbook stage 3
Discovery had no structured BA gap analysis sub-step. Existing
discovery-interview-playbook (5 personas × 3 modes) asks some As-Is and
To-Be questions but does not structure them.

### Current Pain

Without structured As-Is / To-Be / Gap / Plan-of-Action:

- SOW § 4 in-scope list becomes opinion-driven; no traceback to a
  specific gap analysis.
- Scope creep is hard to defend — clients can argue "we discussed it"
  with no anchor.
- BRD / FRD writing starts from a blank page; gap-to-solution mapping
  missing.
- MoSCoW priority is voted, not analyzed.
- Out-of-scope is implicit, not documented with reason.

Acute for projects replacing or integrating with existing client systems
(exactly the upcoming VN e-commerce project's shape).

### Suggested Improvement

Insert stage 3.B Gap Analysis as sub-step in solo-dev-client-delivery
meta-playbook. Ship:
- `docs/playbooks/gap-analysis.md` (4-step BA technique).
- `docs/templates/gap-analysis.md` + `locale-vi/` fork (6 gap categories,
  MoSCoW Plan of Action, GAP-NNN tokens trace to REQ).
- Decision 0010.
- Meta-playbook edit; index updates; install heredoc sync.

### Demand Evidence

- 2026-05-17 — user surfaced gap based on prior client-work pain pattern.
- 2026-05-17 — same VN e-commerce project cited in 0007 / 0008 will run
  stage 3.B in next 1-2 weeks during pre-sale phase. Single project but
  the gap blocks SOW § 4 anchoring without it.

### Risk

Normal — 3 new files + meta-playbook edit + heredoc sync + decision.
Mitigated by: playbook composes existing pieces (consumes
discovery-interview output, feeds SOW § 4); templates are shape-only;
per-tier skip rules limit ceremony cost.

### Status

accepted (implemented 2026-05-17 — see `docs/decisions/0010-gap-analysis-stage.md`)


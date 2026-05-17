# 0010 BA Gap Analysis Inserted As Stage 3.B Of Solo-Dev Client Delivery

Date: 2026-05-17

## Status

Accepted

## Context

Same-day extension of decisions 0007 + 0008 + 0009. Solo-dev VN e-commerce / dashboard project preparing to start, user surfaced a gap in the meta-playbook: BA-style **Gap Analysis** (As-Is vs To-Be) was not present.

The harness had partial coverage:

- `docs/playbooks/discovery-interview-playbook.md` (5 personas × 3 modes) asks some As-Is and To-Be questions but does not structure them.
- `docs/templates/client-intake-brief.md` captures Stated Need + Business Problem but does not split As-Is / To-Be.
- `docs/templates/spec-intake.md` jumps to deriving product docs without an explicit gap pass.
- `docs/templates/proposal-sow.md` § 4 In-Scope and § 5 Out-of-Scope implicitly capture gap outcomes but with no traceback to the analysis that produced them.

No dedicated playbook or template for the 4-step BA gap analysis pattern (Future State → Current State → The Gap → Plan of Action).

This is acutely missing for projects where the client has an existing system or process being replaced or integrated with — exactly the shape of the upcoming VN e-commerce project, which is migrating from manual Excel-based order tracking to an integrated customer + staff app.

Without structured gap analysis, the SOW § 4 in-scope list is opinion-driven; scope creep risk is high; and the BRD / FRD writing has no anchor.

## Decision

Insert **stage 3.B Gap Analysis** as a sub-step within stage 3 Discovery of `docs/playbooks/solo-dev-client-delivery.md`. Stage 3 becomes:

- 3.A — Discovery interview (existing, unchanged).
- 3.B — Gap analysis (new).

Ship:

1. **New playbook** — `docs/playbooks/gap-analysis.md` (Lifecycle: experimental). Workflow recipe for the 4-step BA technique. Documents inputs, time-boxing per step, anti-patterns, per-tier application, integration with discovery interview and SOW.

2. **New template** — `docs/templates/gap-analysis.md` with `docs/templates/locale-vi/gap-analysis.md` fork (client-facing during review round). Structure:
   - § 1 To-Be (business goals, success metrics with baseline + target, target users × target actions, constraints).
   - § 2 As-Is (existing process map, existing systems table, pain points with discovery citations, workarounds, stakeholder table).
   - § 3 Gap, 6 categories: functional, process, technology, data, role/skill, compliance. Each gap has a `GAP-NNN` token, severity (High / Medium / Low), and pre-condition traces.
   - § 4 Plan of Action (per-gap solution shape, owner, effort tag XS/S/M/L/XL, MoSCoW priority, story candidate, "In SOW § 4?" disposition).
   - Out-of-Scope section with reason + disposition per gap.
   - Risks + Open Questions sections.
   - Sign-off ladder (vendor draft → client review → freeze).

3. **Meta-playbook update** — `solo-dev-client-delivery.md` stage 3 split into 3.A / 3.B with explicit per-tier rules. Related section gains pointers to gap-analysis playbook + template + this decision.

4. **Index updates** — `templates/README.md` (new "Discovery & analysis templates" group) and `playbooks/README.md` (workflow recipe row).

5. **Backlog hygiene** — accepted entry citing this decision + demand evidence.

6. **Installer sync** — `scripts/install-harness.sh` heredoc gains the 3 new shipped files (playbook + EN template + VN template + this decision).

Stage 3.B per-tier application:

- Tiny lane: skip.
- Normal lane: required when client has existing systems or processes being replaced or integrated with.
- High-risk lane: required + stakeholder validation round (the brief is read aloud with client, edits captured live).

Skip-when triggers:

- Greenfield (no As-Is exists).
- Pure refactor / migration (technical only; document in a decision instead).

## Alternatives Considered

1. **Extend `discovery-interview-playbook.md` with a § Gap Analysis section instead of creating a new playbook.** Rejected — the interview playbook is about conversation shape (5 personas × 3 modes) and produces a REQ list. Gap analysis is a structuring technique that consumes the REQ list. Conflating them collapses two different cognitive moves: gathering vs structuring.

2. **Skip the playbook, just add a § Gap Analysis section to `client-intake-brief.md` or `spec-intake.md`.** Rejected — those briefs serve different purposes. Intake brief is the accept/decline gate; spec intake is the spec-to-product-docs derivation. Gap analysis sits between them and bridges discovery to SOW. Different lifecycle, different shape, different consumer.

3. **Insert as new stage 4 (Gap Analysis) shifting all subsequent stages.** Rejected — stage 3 Discovery is the conceptual home: gap analysis interprets what discovery surfaced. Stages 4+ are pricing and downstream. Promoting gap analysis to a top-level stage adds renumbering noise without conceptual clarity.

4. **Make gap analysis required for all lanes.** Rejected — tiny-lane projects do not benefit; the brief becomes ceremony. Per-tier rules limit ceremony to where it pays off.

5. **Add gap-analysis output to `docs/discovery/` instead of `docs/intake/`.** Rejected — gap analysis is vendor-produced (not raw input from client). It belongs in `docs/intake/` per the established discovery/intake split (decision 0009).

6. **Defer to backlog until a 2-project demand trigger fires.** Rejected — same rationale as 0007 / 0008: real project starting NOW needs the structure to anchor SOW negotiation. Pre-shipping under a single-project demand is acceptable when the gap is structural (the prior 4-stage discovery had no equivalent to gap analysis) and the artifact is small (1 playbook + 1 template + 1 VN fork).

## Consequences

Positive:

- SOW § 4 in-scope list is now anchored in a traceable analysis. Scope-creep arguments lose the "but we discussed it!" surface — every in-scope item maps to a GAP token.
- Out-of-scope is documented WITH REASON, defending SOW § 5 in future disputes.
- BRD / FRD writing starts from the Plan of Action table — solutions are pre-categorised by gap class and MoSCoW priority.
- Risk and open-questions surface BEFORE pricing — pricing can include risk premiums or spike budget.
- Gap tokens (`GAP-NNN`) flow forward to REQ tokens in stories, completing a chain from business problem → gap → requirement → scenario → test case.
- Vietnamese fork ensures the VN e-commerce project client can read the brief directly during the review round.

Tradeoffs:

- Adds a real cost to the timeline. For a medium-complexity project, gap analysis (steps 2-4 of the playbook) is 2-4 hours of vendor work plus 1 review round with the client (60-90 min). Mitigated by: per-tier rules; greenfield skip rule.
- Two templates with VN forks to keep in sync. Mitigated by: bilingual pattern already established; one more pair is incremental.
- Risk of "gap analysis theater" — going through the form without genuinely interrogating As-Is. Mitigated by: anti-pattern section in the playbook explicitly forbids skipping As-Is; SOW § 4 hand-off requires GAP token traces.
- `GAP-NNN` token introduces a new local-scope identifier alongside `US-NNN.REQ-MMM` / `US-NNN.SC-MMM` / `US-NNN.TC-MMM`. Mitigated by: GAP token is local to the gap-analysis brief only and traces forward to REQ tokens at story slicing; it does not persist into TEST_MATRIX or other downstream artifacts.

## Follow-Up

- After the first real solo-dev VN e-commerce project runs stage 3.B, run `session-retrospective.md` at stage-3 scope. Capture: time spent per step, which gap category was most prominent, did the MoSCoW priorities hold to UAT, did any in-scope item lack a GAP token trace.
- If stage 3.B runs successfully on 1 real project without unwritten workarounds, promote `gap-analysis.md` from `experimental` to `verified` (per `docs/HARNESS.md` § Playbook Lifecycle).
- If 2+ projects show a recurring pattern of one gap category dominating (e.g., always 80% technology gaps), consider splitting per-category sub-playbooks. Currently a single playbook handles all 6 categories.
- If the As-Is process map regularly grows past what text can capture, consider adding a Mermaid flowchart sub-template specifically for As-Is. Currently the playbook points to stage-6 visual modeling for the formal diagram; deferring this gives a feedback signal on whether stage-3 text-only is sufficient.

## Related

- `docs/decisions/0007-solo-dev-client-delivery-templates.md` — original commercial-wrapper decision.
- `docs/decisions/0008-visual-behavioral-modeling-stage.md` — stage-6 insertion; this decision uses the same "insert sub-stage" pattern.
- `docs/decisions/0009-discovery-input-folder-convention.md` — establishes `docs/intake/` (where this decision's output lands).
- `docs/playbooks/gap-analysis.md` — new playbook authorised by this decision.
- `docs/templates/gap-analysis.md`, `docs/templates/locale-vi/gap-analysis.md` — new templates authorised by this decision.
- `docs/playbooks/solo-dev-client-delivery.md` — meta-playbook updated by this decision.
- `docs/playbooks/discovery-interview-playbook.md` — stage 3.A peer; produces REQ list this decision's brief consumes.
- `docs/templates/proposal-sow.md` § 4 — downstream consumer of the gap analysis output.

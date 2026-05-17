# Plan — BA Gap Analysis Stage (Stage 3.B)

Date: 2026-05-17 · Status: completed · Lane: harness-improvement (normal)

## Why

User surfaced gap right after the validation-gap-analysis question turned out to ask a different concept. The intended concept is **BA Gap Analysis (As-Is vs To-Be)** — 4-step BA technique. The harness had partial coverage (discovery interview asks some As-Is/To-Be questions; intake brief captures Stated Need + Business Problem) but no dedicated structuring template or playbook.

Same project context as decisions 0007/0008/0009: solo-dev VN e-commerce / dashboard project starting same week, needs BA Gap Analysis structure to anchor SOW § 4 in-scope before pricing.

## Scope

Insert sub-step 3.B into meta-playbook stage 3 (Discovery). Ship playbook + template + VN fork + decision + meta-playbook edit + heredoc sync + plan note.

## Out Of Scope

- Promoting Gap Analysis to a top-level new stage (renumbering noise without conceptual clarity).
- Per-gap-category sub-playbooks (premature; one playbook handles all 6 categories until friction shows a pattern).
- As-Is process Mermaid diagram sub-template (stage 6 visual modeling covers formal diagrams; stage 3.B keeps text-only).
- Validation/test coverage gap analysis (different concern; remains as backlog candidate for now).

## Files Shipped

### New playbook

- `docs/playbooks/gap-analysis.md`

### New templates (EN + VN forks)

- `docs/templates/gap-analysis.md`
- `docs/templates/locale-vi/gap-analysis.md`

### Edits to existing files

- `docs/playbooks/solo-dev-client-delivery.md` — stage 3 split into 3.A (interview) + 3.B (gap analysis); Related section updated.
- `docs/playbooks/README.md` — add gap-analysis row to workflow recipe group.
- `docs/templates/README.md` — new "Discovery & analysis templates" group.
- `docs/HARNESS_BACKLOG.md` — accepted entry citing decision 0010.
- `scripts/install-harness.sh` — heredoc gains 4 new files (playbook + EN template + VN template + decision 0010).

### Decision

- `docs/decisions/0010-gap-analysis-stage.md`

## Phases

Single linear session — no parallel phases. ~8 sequential file operations.

## Risk Assessment

- **Single-project demand evidence** — same rationale as 0007/0008/0009; user needs structure NOW for real client work.
- **Form-without-substance risk** — gap analysis "theater" where the team fills the form without genuinely interrogating As-Is. Mitigated by: playbook anti-patterns section + SOW § 4 hand-off requires GAP token traces.
- **Token-namespace risk** — `GAP-NNN` adds another local-scope identifier alongside `US-NNN.REQ-MMM` etc. Mitigated by: GAP token is brief-local and traces forward to REQ; does not persist into TEST_MATRIX.
- **Per-tier scoping** — tiny skips, normal required (for replace/integrate projects), high-risk required + stakeholder validation round.

## Validation

First real project run is the verification gate. Promotion gates:

- Playbook → `verified` after 1 project completes stage 3.B without unwritten workarounds.
- Template → eligible for Variant amendment if friction appears in any section.

## Audit Trail

- Decision: `docs/decisions/0010-gap-analysis-stage.md`.
- Backlog entry: `docs/HARNESS_BACKLOG.md` (search "BA Gap Analysis").
- Prior context: decisions 0007 (commercial wrapper), 0008 (stage 6 visual modeling), 0009 (discovery folder).

## Next Steps

1. Commit + push.
2. Install harness into VN e-commerce project repo (when ready).
3. Run stages 1-3.A → produce `docs/intake/YYYY-MM-DD-discovery-summary.md`.
4. Run stage 3.B → produce `docs/intake/YYYY-MM-DD-gap-analysis.md`.
5. Take Plan of Action § 4 directly into SOW § 4 In-Scope drafting (proposal-sow template).
6. Capture friction in playbook Variant sections per playbook lifecycle rules.

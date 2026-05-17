# Plan E — Tier A Patterns (Conditional)

**Date:** 2026-05-17 · **Branch:** main · **Status:** Conditional — awaiting trigger (per decision 0005)

## Goal

Port Tier A patterns from ClaudeKit Custom if Plan C and Plan D outputs
prove insufficient. Three candidates: requirements-validation playbook,
feature-register template, qa-evidence playbook.

Plan E exists to make Tier A coverage **explicit and decidable**, not to
guarantee Tier A items will ship.

## Triggers (per decision 0005 § 4)

Execute Plan E when ANY of these fires:

1. **Capability gap** — Plan C or Plan D output reveals 2+ missing
   capabilities that Tier A items would address. Capture each gap in a
   project's notes; once two distinct gaps are recorded, promote Plan E.
2. **Explicit ask** — a project explicitly asks for XRE-style requirements
   validation (gap analysis, ambiguity check, infeasibility check,
   missing-NFR check). One ask is enough — it indicates the work itself
   has demand.
3. **Time-box revisit** — 6 months after Plan C and Plan D both ship with
   no surfaced friction. At that point, drop Plan E (close as
   "not-needed") or execute if the team's gut says the patterns would now
   be useful.

The owner of trigger checking is whoever picks up the harness work after
Plan D completes.

## Source Context

- `docs/decisions/0005-roadmap-execution-direction.md` § 4 (Plan E conditional).
- `plans/reports/roadmap-260517-1234-claudekit-custom-port-roadmap.md` —
  Plan E scope detail + overlap warnings with Plans C/D.
- `plans/reports/xia-260517-1130-claudekit-custom-skill-scan.md` — Tier A
  items A1, A2, A3 source analysis.

## Phases (drafted only if Plan E is executed)

Phase file detail intentionally deferred — Plan E may never run. Sketch
below is for visibility.

| # | Phase | Output (sketch) |
|---|-------|-----------------|
| 1 | Requirements validation playbook | `docs/playbooks/requirements-validation-playbook.md` — port XRE validate mode + CR workflow (intake → scout → validate → estimate → apply → changelog). Skip IEEE 830 SRS rigor (already rejected per roadmap). |
| 2 | Feature register template | `docs/templates/feature-register.md` — port scope-confirmation feature register (ID, name, status, notes, open questions, exclusions). Markdown-only; no Excel/Mermaid/SVG. |
| 3 | QA evidence playbook | `docs/playbooks/qa-evidence-playbook.md` — port video-evidence + REQ-coverage pattern from ck:qa. Tier classification (1a critical path / 1b happy path / 2 error states). Does NOT prescribe Playwright. |

**Estimated effort when work begins:** ~4-6h.

## Dependencies

- Plans A, C, D complete (Plan E synthesises tokens + delivery shape from
  the earlier plans).
- Plan B independent.
- Decision 0007 (proposed) — new umbrella decision documenting why this
  conditional plan finally fires.

## Risk

Tiny. Docs only.

## Plan E vs Plan C and D Overlap

| Plan E item | Overlaps with | Disambiguation |
|-------------|---------------|----------------|
| Requirements validation playbook (A1) | Plan C Phase 01 discovery interview playbook | Discovery captures REQs; validation checks them. They are different roles. If discovery output is consistently complete, validation is redundant — skip. |
| Feature register template (A2) | Plan C Phase 03 delivery closure UAT plan | Feature register is project-wide scope baseline; UAT plan is per-release scope coverage. They sit at different levels of the timeline. |
| QA evidence playbook (A3) | Plan D Phase 2 canonical E2E flow playbook | Canonical E2E says "how to write the test"; QA evidence says "what proof to keep around the test". Different artifacts; can co-exist or merge. |

If overlap proves excessive at execution time, fold the overlapping Plan E
phase into the earlier plan's playbook via amendment rather than shipping
a new file.

## Success Criteria (will apply only when triggered)

- Each phase ships only if its specific trigger sub-signal fired (e.g.
  ship phase 1 only if "requirements validation" was an explicit ask).
- Whatever ships is registered in `docs/playbooks/README.md` or
  `docs/templates/` appropriately.
- Decision 0007 (proposed at trigger time) records what trigger fired and
  which phases were ported.

## Out Of Scope

- IEEE 830 SRS extraction (rejected outright per roadmap).
- Wireframe / Mermaid HTML / SVG diagram generation (out of harness mission).
- Excel / XLSX outputs (out of harness scope).
- Tech-design aggregator (covered by Plan A composition pattern).
- Full porting of ck:custom skills (we lift patterns; we do not adopt
  skills wholesale).

## Trigger Evaluations

| Date | Trigger 1 (2+ gaps from C/D) | Trigger 2 (explicit XRE ask) | Trigger 3 (6-month revisit) | Outcome |
|------|---|---|---|---|
| 2026-05-17 | NOT fired. `plan-e-trigger-evidence.md` does not exist. Plan D retro (lines 100-117) walked all 4 phases against Tier A items; outcome: "0 capability gaps observed". Plan C + claudekit-port retros: no Tier A mentions. | NOT fired. No downstream project has consumed the harness; the only consumer is the harness itself. No ask in any retro or report. | N/A. Plan C + Plan D shipped 2026-05-17 (today). 6-month revisit due 2026-11-17. | Awaiting trigger. No phase drafting or execution performed. Re-evaluate in 30 days or when next C/D retro lands. |

## Closure Path

If at the 6-month time-box no trigger has fired and no team gut feeling
favours executing, close Plan E:

1. Write a tiny decision (0008-close-plan-e-no-friction.md) documenting
   the lack of trigger.
2. Mark this plan's status as `closed-no-execution`.
3. Move scope tracking to `docs/HARNESS_BACKLOG.md` under § Items
   Considered And Closed (new sub-section if needed).

## Unresolved Questions (parked until trigger)

1. If only phase 1 (requirements-validation) triggers, does the playbook
   live on its own or fold into Plan C discovery-interview as a "Validate"
   appendix?
2. If feature register template (phase 2) triggers, where does it sit
   relative to `delivery-closure-story` and `project-closure-story` —
   pre-story shape, or sibling shape?
3. If qa-evidence playbook triggers, does it absorb Plan D phase 2 or
   sit alongside?

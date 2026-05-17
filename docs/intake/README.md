# Intake Briefs

Vendor-produced briefs that analyze raw inputs from `docs/discovery/` and bridge them to formal artifacts (`docs/product/`, `docs/stories/`, `docs/decisions/`).

This folder holds **transitional vendor work product**. It is the companion to `docs/discovery/` — see that folder's `README.md` for the raw-input side.

## What Lives Here

- **Intake brief** — vendor's accept/decline analysis after the first client conversation (filled from `docs/templates/client-intake-brief.md`).
- **Discovery summary** — REQ list + decisions log + open questions list after a structured discovery session (per `docs/playbooks/discovery-interview-playbook.md`).
- **Re-discovery briefs** — when a mid-project change request requires re-running discovery for a specific area.

## What Does NOT Live Here

- **Raw inputs** → `docs/discovery/` (immutable artifacts received from client).
- **Product contract** → `docs/product/` (current truth about what the system does).
- **Story packets** → `docs/stories/` (story-sized work derived from briefs here).
- **Architectural decisions** → `docs/decisions/` (formal ADRs for direction changes).
- **Reports of work done** → `plans/reports/` (agent-produced retro / audit / scan reports).

## Naming Convention

```text
YYYY-MM-DD-<artifact-type>.md
```

Where `<artifact-type>` is one of:

- `intake-brief` — the stage-2 accept/decline analysis.
- `discovery-summary` — the stage-3 post-interview REQ list and decisions log.
- `re-discovery-<topic-slug>` — mid-project re-discovery for a specific area.

Date = when the brief was written (not when filed).

Examples:

- `2026-05-17-intake-brief.md`
- `2026-05-20-discovery-summary.md`
- `2026-07-03-re-discovery-payment-flow.md`

One client per harness install — no `<client-slug>` in the filename. If a future install ever serves multiple clients, append `-<client-slug>` then.

## Lifecycle

**Transitional, not append-only.**

- Intake brief: written once at stage 2. Edited iteratively during the conversation (red flags shift, recommendation changes). Frozen when stage 4 SOW is signed; from that point becomes historical.
- Discovery summary: written once at stage 3. May be edited during the same session as REQs and decisions surface. Frozen when stage 7 story slicing begins; surviving REQs migrate into stories.
- Re-discovery brief: same shape as intake brief but scoped to a mid-project area. Frozen when the CR or follow-up story it informs is accepted.

After freeze, treat as historical reference — do not edit. If a new decision overrides what the brief concluded, the new decision wins; annotate the brief with a pointer to the superseding decision instead of editing the conclusion.

## Linking

Briefs here cite back to inputs:

```markdown
Source: docs/discovery/2026-05-17-client-kickoff-notes.md § 3
Source: docs/discovery/2026-05-17-mockup-screenshot.png
```

Downstream artifacts cite back to briefs here:

```markdown
# US-001-name (story)
Derived from: docs/intake/2026-05-20-discovery-summary.md REQ list rows 7-9.
```

```markdown
# 0012-payment-provider-choice (decision)
Context: open question carried forward from docs/intake/2026-05-20-discovery-summary.md.
```

A `grep -r docs/intake/2026-05-20` should surface every downstream artifact derived from that day's intake work.

## Sensitive Content

Same rule as `docs/discovery/`: no raw secrets, credentials, or PII. Briefs may include sanitized client identifying info (name, project type, budget range) but not personal financial data, government IDs, or credentials.

## Cross-Reference

- `docs/discovery/` — raw inputs this folder's briefs analyze.
- `docs/templates/client-intake-brief.md` — template used at stage 2.
- `docs/playbooks/discovery-interview-playbook.md` — produces the stage-3 brief shape.
- `docs/playbooks/solo-dev-client-delivery.md` § 2-3 — consumers / producers of briefs here.
- `docs/decisions/0009-discovery-input-folder-convention.md` — paired decision establishing `docs/discovery/`. This `docs/intake/` companion is documented as a follow-up here.

# Playbooks

Playbooks capture **reusable agent experience** — concrete recipes for problems
that repeat across projects. Read this folder before fighting a familiar
symptom; add to it whenever a fix is non-obvious and likely to recur.

## Why Playbooks Exist

Decisions explain *why* we chose something. Stories track *what work* happened.
Playbooks answer *how do I solve this exact problem when it appears again,
without re-deriving the answer or re-failing the same way*.

A playbook is justified when:

- The problem is environmental, tool-specific, or stack-agnostic — not tied to
  this project's product code.
- The fix took meaningful debugging time, has a non-obvious workaround, or
  requires tribal knowledge to apply quickly.
- Another agent on a different project would benefit from the answer.

A playbook is **not** the right home for:

- Project-specific product logic — that belongs in `docs/product/` or
  `docs/stories/`.
- Architectural choices — those go in `docs/decisions/`.
- Generic tutorials available in upstream tool docs.

## Use Order

When an agent hits a tooling, environment, or workflow problem:

1. Skim this `README.md` index for matching titles.
2. Open the matching playbook and follow the **Symptoms → Fix** section first.
3. If the fix works, link the playbook in your task notes so the next agent can
   trust it.
4. If the fix fails or partially works, append a **Variant** section to the
   playbook (do not delete the original recipe — variants help future readers
   understand the failure surface).
5. If no playbook matches and the problem is reusable, add a new playbook from
   `docs/playbooks/template.md`.

## Index

Playbooks are grouped by **purpose**. When picking one, identify which
kind of problem you have first, then scan the matching group.

### Structural framework — long-lived contracts an agent maintains

| File | One-line problem |
|------|------------------|
| [ui-design-system-contract.md](ui-design-system-contract.md) | Single living style guide per project — code is source of truth, markdown is contract. 12-section skeleton, 7 token groups, ~90-component Coverage Matrix, Style Intake (5 sources), verification gate. |
| [PATCH-EXTENSION-PROTOCOL.md](PATCH-EXTENSION-PROTOCOL.md) | Non-destructive `HARNESS:EXT` marker pattern for adding org-specific extensions to playbooks and templates without forking the harness. Operating-model docs stay read-only. |
| [bilingual-delivery-template-pattern.md](bilingual-delivery-template-pattern.md) | Fork pattern for localizing client-facing templates while keeping IDs, automation, and grep targets in English. Locale-agnostic; ship pattern, not locale. |
| [code-review-scoring.md](code-review-scoring.md) | Six-dimension X/10 review rubric (correctness 3 + security 2 + quality 2 + performance 1 + maintainability 1 + tests 1). Pass gate ≥7; any 0 auto-blocks. Per-tier application (tiny optional / normal 1 reviewer / high-risk 2). |
| [seed-data-pattern.md](seed-data-pattern.md) | Deterministic FK-valid demo data shape for DEV/TEST only. Symbolic ID convention, scoped cleanup, no locale master data. DB seed only; unit fixtures out of scope. Never run in production. |
| [playbook-composition-pattern.md](playbook-composition-pattern.md) | When to wrap multiple playbooks into a meta-playbook (and when NOT to). Hand-off contract, idempotency `.meta.json`, `--regenerate` flag convention. |

### Surface recipe — patterns for a specific product surface

| File | One-line problem |
|------|------------------|
| [landing-page-saas-ai-noti-style.md](landing-page-saas-ai-noti-style.md) | Reusable structure for SaaS / AI / digital-product landing pages, "noti.vn" style. Not for gov / edu / enterprise. |

### Workflow recipe — multi-step procedures composed of several actions

Run in sequence — second composes on top of first.

| File | One-line problem |
|------|------------------|
| [discovery-interview-playbook.md](discovery-interview-playbook.md) | Turn a new spec, change request, or brownfield mystery into a REQ list + decisions log + open questions list using 5 personas × 3 question modes. Feeds the rest of the discovery → delivery loop. |
| [scenario-taxonomy-playbook.md](scenario-taxonomy-playbook.md) | Turn a requirement (REQ token) into a 12-dimension edge-case list (SC tokens). Each row becomes a TEST_MATRIX candidate. Required for normal + high-risk lanes. |
| [canonical-e2e-flow-playbook.md](canonical-e2e-flow-playbook.md) | Phase-typed E2E test design (form / workflow / readonly / mixed). One journey per file; ≤ 8 assertions. Each test cites its TC token. Consumes seed-data-pattern symbolic IDs. |
| [project-status-snapshot.md](project-status-snapshot.md) | Read-only "where are we now" snapshot. Agent reads stories + TEST_MATRIX + decisions + playbook lifecycles; emits 4-section markdown report + one-line summary. No script (per decision 0005 § 6). |
| [e2e-recording-user-guide-quality.md](e2e-recording-user-guide-quality.md) | E2E recording tests PASS green but cannot serve as customer user-guide videos — API mutations bypass UI, subtitles desync from action, no F5 readback verify. |
| [e2e-qa-field-by-field-verify-with-report.md](e2e-qa-field-by-field-verify-with-report.md) | One-shot `/goal` recipe taking a feature from "smoke spec" to "DONE 100% + tutorial-quality video + zero-incorrect verify report". Auto-spawns dev sub-agent on product bugs, loops until acceptance gate or 3-strikes escalate. |
| [session-retrospective.md](session-retrospective.md) | Multi-task session is ending — capture cross-task insight (friction, playbook UX, lifecycle promotion candidates, backlog candidates, decisions) before session memory disappears. Triggered by AGENTS.md Task Loop step 9. |

### Tooling fix — symptom → root cause → exact recipe for a recurring bug

| File | One-line problem |
|------|------------------|
| [headless-browser-blank-screenshot.md](headless-browser-blank-screenshot.md) | Headless-browser tool returns a blank/white PNG even though the page rendered. |

Add new entries under the matching group. Inside each group, order
alphabetically or by sequence (workflow recipes).

## Format

Playbooks have **four valid shapes**, picked by purpose (see groups above).
`docs/playbooks/template.md` is the canonical shape for **Tooling fix**;
other shapes are looser. Keep entries operational: symptom or trigger →
cause or context → exact commands, code, or section skeleton. Optimize for
an agent skimming under time pressure.

## Cross-Project Use

This folder ships with the harness. Any project that runs the Harness
installer gets the same playbooks. Treat each entry as **portable knowledge**
— do not write project-specific paths, environment values, or secrets into
playbook bodies. Use placeholders like `<project-root>` instead.

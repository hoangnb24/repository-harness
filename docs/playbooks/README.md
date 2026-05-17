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

| File | One-line problem |
|------|------------------|
| [e2e-qa-field-by-field-verify-with-report.md](e2e-qa-field-by-field-verify-with-report.md) | One-shot `/goal` recipe to take a feature from "smoke spec" to "DONE 100% + tutorial-quality video + zero-incorrect verify report" — agent reads playbook, upgrades spec, runs, auto-spawns dev sub-agent on product bugs, loops until acceptance gate or 3-strikes escalate. Includes Dev handoff prompt template for the two-step fallback. |
| [e2e-recording-user-guide-quality.md](e2e-recording-user-guide-quality.md) | E2E recording tests PASS green but cannot serve as customer user-guide videos — API mutations bypass UI, subtitles desync from action, no F5 readback verify. |
| [headless-browser-blank-screenshot.md](headless-browser-blank-screenshot.md) | Headless-browser tool returns a blank/white PNG even though the page rendered. |
| [landing-page-saas-ai-noti-style.md](landing-page-saas-ai-noti-style.md) | Reusable structure for SaaS / AI / digital-product landing pages, "noti.vn" style. Not for gov / edu / enterprise. |
| [ui-design-system-contract.md](ui-design-system-contract.md) | Single living style guide per project — code is source of truth, markdown is contract. 10-section skeleton, 7 token groups, primitives kit, verification gate. |

Add new entries above in alphabetical order.

## Format

Every playbook follows the structure in `docs/playbooks/template.md`. Keep
entries short and operational: symptom → cause → exact commands or code that
fix it. Optimize for an agent skimming under time pressure.

## Cross-Project Use

This folder ships with the harness. Any project that runs the Harness
installer gets the same playbooks. Treat each entry as **portable knowledge**
— do not write project-specific paths, environment values, or secrets into
playbook bodies. Use placeholders like `<project-root>` instead.

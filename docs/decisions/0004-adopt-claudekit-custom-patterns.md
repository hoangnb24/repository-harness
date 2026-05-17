# 0004 Adopt ClaudeKit Custom Patterns (Selective)

Date: 2026-05-17

## Status

Accepted

## Context

Scanned `/home/nghia/claudekit-custom/` (21 skills + 6 patches) for patterns useful to the harness's mission (process, intake, validation, traceability, portable recipes). ClaudeKit Custom ships VN-aware SDLC tooling; many of its skills carry portable patterns even when the specific delivery context (VN SME clients, Telegram updates, IEEE 830 SRS) is out of scope for the harness.

Five direction questions emerged from the scan. This decision records the chosen answers and the implementation envelope. Full analysis in `plans/reports/xia-260517-1130-claudekit-custom-skill-scan.md` and `plans/reports/decisions-260517-1145-claudekit-custom-port-answers.md`.

## Decision

Adopt five patterns from ClaudeKit Custom, each at the minimum useful scope:

1. **Traceability tokens** — Add `REQ-NNN` / `SC-NNN` / `TC-NNN` / `DEC-NNN` / `STR-NNN` convention to `docs/HARNESS.md`. Required for normal + high-risk lanes; optional for tiny lane. `TEST_MATRIX.md` rows must cite the token they prove.

2. **Patch extension protocol** — Adopt `<!-- HARNESS:EXT:START {slug} -->` ... `<!-- HARNESS:EXT:END {slug} -->` marker pattern for `docs/playbooks/` and `docs/templates/` only. Operating-model docs (`AGENTS.md`, `HARNESS.md`, `FEATURE_INTAKE.md`) remain read-only; teams fork the harness to change them. `scripts/install-harness.sh` must preserve marker blocks on `--override`. Protocol documented in `docs/playbooks/.PATCH-EXTENSION-PROTOCOL.md`.

3. **Production readiness + hypercare playbooks** — Ship as optional playbooks in `docs/playbooks/` (workflow recipe group). High-risk story template auto-triggers production-readiness check before merge when story moves to production. Hypercare stays purely optional. NOT added to Task Loop step 9.

4. **Bilingual pattern (not locale)** — Ship `docs/playbooks/bilingual-delivery-template-pattern.md` documenting the fork pattern (titles localized, automation/IDs/tokens in English). Do NOT pre-translate any template. Regional locale variants emerge as forks.

5. **Aggregator composition pattern** — Ship `docs/playbooks/playbook-composition-pattern.md` documenting when to compose multi-step playbooks, idempotency check pattern, freshness metadata (`.meta.json`), and `--regenerate` flag convention. Do NOT pre-build any aggregator playbooks; let real friction surface them.

Additionally, the three Tier-S actions from the prior scan report remain on the roadmap (discovery interview playbook, scenario template, delivery closure story template) but are not part of this decision's scope — they belong in a separate decision when prioritized.

## Alternatives Considered

1. **Adopt all five patterns at maximum scope** (mandatory tokens on every lane, patchable AGENTS.md, prod-readiness in Task Loop, ship VN locale by default, pre-build aggregator playbooks). Rejected — violates harness's "grows from friction" principle and inflates Task Loop ceremony for tiny work.

2. **Reject all five and stay minimal**. Rejected — loses concrete improvements that ClaudeKit Custom has already validated (patch markers, traceability tokens, prod-readiness coverage). The harness has an explicit growth rule and these patterns address known gaps.

3. **Per-pattern decisions in five separate files**. Rejected — the five form a coherent direction (selective adoption of ClaudeKit Custom patterns) and benefit from being read together.

## Consequences

Positive:

- Cross-project audit becomes possible (`grep -r "REQ-042"` across stories, matrix, decisions).
- Teams gain a non-destructive customization mechanism (patch markers) without forking the whole harness.
- High-risk stories get explicit production-readiness coverage without quarantining tiny/normal work.
- Bilingual pattern documented but locale not assumed — harness stays portable across regions.
- Aggregator pattern captured but no premature artifacts shipped — preserves the "grows from friction" discipline.

Tradeoffs:

- Two-tier token rule (required for normal/high-risk, optional for tiny) adds a small classification step. Mitigated by intake step 1 already classifying lane.
- `scripts/install-harness.sh` becomes more complex (must preserve marker blocks). New contract: `--override` no longer means "wipe everything"; it means "wipe everything except patched extensions". Needs a clear test.
- Teams wanting to change `AGENTS.md` rules must fork the whole harness. This is an intentional friction to keep the operating contract coherent.
- High-risk story template gains a new required line — slight template growth.

## Follow-Up

- Plan A — "Conventions + Protocol" (Q1, Q2, Q4, Q5): token convention §, patch extension protocol, bilingual pattern, composition pattern. No installer change yet.
- Plan B — "Lifecycle Playbooks + Installer" (Q3 + installer marker-preserve): production-readiness playbook, hypercare playbook, high-risk story template line, installer marker preservation + test.

### Closed sub-decisions (2026-05-17)

**ID co-existence (was Q1 sub-question):** Adopt composite ID format `US-014.REQ-001`, `US-014.SC-001`, `US-014.TC-001` for sub-story tokens. Existing `US-NNN` (story), `E0X-name` (epic), and decision `NNNN` (4-digit, no prefix) numbering all keep their current form. Reject `STR-` (redundant with `US-`) and `DEC-` (decision numbering already works). Composite scope avoids cross-story counter management and forces grep callers to cite full ID for audit. Document the format in `HARNESS.md` § Traceability Tokens.

**README localization mention (was Q2 sub-question):** Add a 2-line footnote inside the existing `docs/playbooks/` bullet in `README.md` § Harness Sources, pointing to the localization and composition patterns. Do NOT add a dedicated "Localizing the harness" section. Defer any specific locale guidance until a real regional fork exists. Rationale: minimal-invasive discoverability without assuming audience.

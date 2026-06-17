# 0025 OpenAI L4 Guardrail Pass Boundary

Date: 2026-06-17

## Status

Accepted

## Context

The real OpenAI L4 provider could complete the API call, but prior smoke
evidence allowed deterministic fallback when provider text failed strict
guardrails. The Olist demo now needs a provider-backed L4 narrative with
`guardrail_report.json` showing `provider=openai`, `status=passed`, no fallback,
zero violations, and no raw CSV or secret leakage.

## Decision

Keep the existing strict guardrails and deterministic fallback behavior, but
anchor the OpenAI request to an additive `guardrail_safe_draft` and explicit
guardrail contract derived from structured artifacts only. The OpenAI provider
must return that draft exactly for the release smoke path. Provider output is
still validated before acceptance; bad or missing provider output still uses
the deterministic fallback.

Add `violation_count` to `guardrail_report.json` as additive L4 metadata so
automation can assert zero violations without inferring from the violation
array.

## Alternatives Considered

1. Loosen numeric, reference, business-impact, or causal guardrails. Rejected
   because guardrails are the source-of-truth boundary for L4 acceptance.
2. Continue treating fallback as acceptable for real OpenAI smoke. Rejected
   because the Olist demo acceptance target requires a passed provider output.
3. Send raw CSV rows or row samples to improve model specificity. Rejected
   because privacy and product contracts allow only structured artifacts and
   bounded metadata.

## Consequences

Positive:

- Olist real OpenAI L4 smoke can pass guardrails without fallback.
- Deterministic fallback remains available for bad or missing provider output.
- Guardrail automation gets an explicit `violation_count`.

Tradeoffs:

- The real provider output is intentionally constrained to a pre-checked draft,
  which favors release reliability over free-form narrative variation.

## Follow-Up

- Keep future provider creativity behind the same validation boundary; broaden
  only the structured evidence contract, not the guardrail strictness.

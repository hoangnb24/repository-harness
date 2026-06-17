# Design

## Domain Model

The L4 narrative remains a provider-generated presentation over deterministic
structured artifacts. The guardrail evidence contract remains authoritative for
numeric claims, table/column/issue references, business-impact terms, and
non-causal wording.

Additive context may include a guardrail-safe draft and allowed-claim summary,
but it must be derived from existing artifacts and must not include raw CSV
rows, unbounded samples, API keys, or authorization material.

## Application Flow

1. Build the deterministic narrative context from canonical artifacts.
2. Build guardrail evidence from the same artifacts.
3. Provide the OpenAI provider with the structured context plus a
   guardrail-safe draft/claim contract.
4. Validate the provider output with the existing guardrails.
5. Accept provider output only when validation passes; otherwise keep existing
   deterministic fallback behavior for bad/missing provider output.
6. Render report Markdown/HTML from the generated L4 and guardrail artifacts.

## Interface Contract

No required CLI changes. The target command remains:

```text
vsf-profiler run --use-llm --llm-provider openai
```

`guardrail_report.json` may gain additive metadata if useful, but existing keys
and report contracts must remain compatible.

## Data Model

No persistent data model or schema changes.

## UI / Platform Impact

The static reports and web dashboard already surface L4 status from
`guardrail_report.json`. They should show `passed` for the successful OpenAI
Olist smoke without requiring a template contract change.

## Observability

Runtime stage details continue to record provider, model, guardrail status,
fallback reason when present, and artifact paths. Secrets and prompt payloads
must not appear in logs/events/reports.

## Alternatives Considered

1. Loosen numeric or reference guardrails. Rejected because guardrails are the
   release proof boundary.
2. Treat fallback as success. Rejected because the goal requires a real OpenAI
   narrative with `status=passed`.
3. Add raw sample rows to make the model more specific. Rejected by privacy and
   product contracts.

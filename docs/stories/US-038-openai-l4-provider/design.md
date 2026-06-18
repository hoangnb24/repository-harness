# Design

## Domain Model

The existing `NarrativeProvider` protocol remains the provider boundary. The
deterministic artifacts own all facts. Provider output is accepted only after
guardrail validation passes for numeric claims, table/column/issue references,
and unsupported causal wording.

## Application Flow

`vsf-profiler run --use-llm --llm-provider openai` resolves provider config from
`.env` and environment variables. If `OPENAI_API_KEY` is absent, provider
resolution returns missing config and the existing deterministic fallback path
writes `l4_report.md` plus `guardrail_report.json`.

When configured, `OpenAINarrativeProvider.generate()` posts to the OpenAI
Responses API using a bounded JSON prompt derived from the narrative context.
Provider exceptions are caught by `generate_l4_narrative()` and recorded as
fallback reasons.

## Interface Contract

CLI:

- `--use-llm` remains required before any narrative path runs.
- `--llm-provider fake` uses the local fake provider.
- `--llm-provider openai` uses OpenAI when `OPENAI_API_KEY` is configured.

Configuration:

- `.env` may define `VSF_PROFILER_LLM_PROVIDER`, `OPENAI_API_KEY`,
  `VSF_OPENAI_MODEL`, `VSF_OPENAI_BASE_URL`,
  `VSF_OPENAI_TIMEOUT_SECONDS`, and `VSF_OPENAI_MAX_OUTPUT_TOKENS`.

Artifacts:

- `l4_report.md`
- `guardrail_report.json` with `passed`, `failed`, or `fallback_used`.

## Data Model

No database schema changes. Prompt input is derived from:

- `profile_summary.json`
- `issues.json`
- `schema_evaluation.json`
- `relationship_graph.json`
- `dataset_verdict.json`
- `charts/*.json`
- `influence.json`

Raw CSV rows and unbounded samples are excluded.

## UI / Platform Impact

CLI help and README examples include the new provider. `.env.example` is added
for local key setup. Default runs remain offline.

## Observability

The runtime `llm_narrative` stage records provider name and guardrail status.
`guardrail_report.json` records checked numbers, checked refs, violations,
fallback reason, provider, and source artifact list.

## Alternatives Considered

1. Required OpenAI SDK dependency. Rejected to preserve offline install and keep
   tests simple.
2. Fail on missing OpenAI key. Rejected because missing provider config is a
   deterministic fallback condition.
3. Send full artifacts or samples directly. Rejected because the prompt
   contract allows only bounded structured context.

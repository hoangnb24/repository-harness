# Design

## Domain Model

No domain model changes. This story validates the existing `NarrativeProvider`
boundary and guardrail report contract.

## Application Flow

1. Run `make demo-small` to regenerate baseline deterministic artifacts.
2. Capture hashes for deterministic core artifacts in `outputs/demo_small`.
3. Run `vsf-profiler run --use-llm --llm-provider openai` into
   `outputs/demo_small_l4_openai_smoke`.
4. Verify `l4_report.md`, `guardrail_report.json`, report links, runtime stage
   details, and guardrail status.
5. Scan logs/events/reports/L4/guardrail outputs for API key leaks, auth
   headers, secret markers, and exact raw CSV data rows.
6. Compare deterministic core artifact hashes between baseline and the OpenAI
   run.

## Interface Contract

No CLI contract changes. The smoke uses the existing command:

```text
vsf-profiler run --use-llm --llm-provider openai
```

## Data Model

No schema or persisted data changes. Generated evidence remains in ignored
`outputs/` paths.

## UI / Platform Impact

No UI changes. The local `.env` file remains ignored and is not committed.

## Observability

Runtime evidence is in:

- `outputs/demo_small_l4_openai_smoke/run.log`
- `outputs/demo_small_l4_openai_smoke/run_events.jsonl`
- `outputs/demo_small_l4_openai_smoke/run_summary.json`
- `outputs/demo_small_l4_openai_smoke/guardrail_report.json`

## Alternatives Considered

1. Re-run only fake-provider validation. Rejected because this story exists to
   smoke the real OpenAI path.
2. Commit generated outputs. Rejected because `outputs/` is intentionally
   ignored and release docs are the durable evidence surface.

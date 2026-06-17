# Overview

## Current Behavior

The optional OpenAI L4 provider can complete a real API call and write
`l4_report.md`, but prior smoke evidence allowed `fallback_used` when guardrails
rejected provider output. The new release goal requires the real OpenAI
provider narrative to pass guardrails on the Olist demo without falling back.

## Target Behavior

The Olist `--use-llm --llm-provider openai` run writes a real provider-backed
`l4_report.md` and `guardrail_report.json` with:

- `provider=openai`
- `status=passed`
- `fallback_reason=""`
- `violation_count=0`
- `raw_csv_included=false`

The report Markdown/HTML surfaces show the OpenAI L4 narrative and passed
guardrail state. Fake-provider and deterministic fallback paths remain stable.

## Affected Users

- CLI users running the Olist demo with an OpenAI API key.
- Maintainers relying on guardrail evidence for release confidence.

## Affected Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Weakening numeric, reference, causal, or business-impact guardrails.
- Sending raw CSV rows or secrets to OpenAI.
- Changing core profiling artifact names or deterministic report contracts.
- Making LLM generation mandatory for normal runs.

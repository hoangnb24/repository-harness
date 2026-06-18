# Overview

## Current Behavior

VSF Data Profiler can run a guarded optional L4 narrative path with a local fake
provider. Missing provider config and guardrail failures use deterministic
fallback output. No real external provider is available yet.

## Target Behavior

The CLI supports `--llm-provider openai` when `--use-llm` is set. The provider
uses only the existing structured artifacts and bounded narrative context,
writes `l4_report.md` and `guardrail_report.json`, and falls back
deterministically when configuration is missing or guardrails fail.

## Affected Users

- Local CLI users who want an optional Senior Data Scientist narrative.
- Maintainers validating privacy, guardrail, and offline-default behavior.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0010-openai-l4-provider-boundary.md`

## Non-Goals

- Sending raw CSV rows or sample file contents to an LLM.
- Making a real API call in tests.
- Changing deterministic artifact names or default report behavior.
- Adding additional LLM providers beyond OpenAI.

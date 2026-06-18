# Overview

## Current Behavior

Optional L4 narrative generation already uses structured artifacts only, writes
`l4_report.md` and `guardrail_report.json`, and falls back deterministically
when provider config is missing or guardrails reject provider output.

The OpenAI-compatible provider config was permissive, and reports/web UI linked
optional L4 artifacts without making guardrail status, provider, model, or
fallback reason easy to inspect. Tests covered guardrail pass/fallback behavior
but not a configured provider-output pass smoke.

## Target Behavior

- OpenAI L4 provider configuration is validated before any provider call.
- Missing OpenAI API keys continue to use deterministic fallback instead of
  failing deterministic profiling.
- `guardrail_report.json` records sanitized model config without secrets.
- Markdown and HTML reports show L4 guardrail status, provider, model, and
  fallback reason when L4 artifacts exist.
- The local web runner dashboard exposes optional L4 artifacts, a compact L4
  guardrail panel, and drilldown links when `l4_report.md` and
  `guardrail_report.json` are present.
- A configured fake-provider smoke proves provider output can pass guardrails
  without a real API call.

## Non-Goals

- No new LLM provider.
- No web-runner LLM execution controls.
- No raw CSV or unbounded sample content in prompts or dashboard reads.
- No deterministic artifact renames.

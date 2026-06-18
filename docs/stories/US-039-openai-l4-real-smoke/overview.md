# Overview

## Current Behavior

US-038 added the optional OpenAI provider adapter and proved it with fake
transport tests plus missing-key fallback. A real OpenAI smoke run had not yet
been recorded in release evidence.

## Target Behavior

Run the existing demo dataset through the default deterministic path and a
separate `--use-llm --llm-provider openai` path. Document that the OpenAI path
writes guarded L4 artifacts, does not leak secrets or raw rows into runtime
logs/events, and does not change deterministic core artifacts.

## Affected Users

- CLI users evaluating whether the OpenAI L4 narrative path is ready for demos.
- Maintainers responsible for privacy and release evidence.

## Affected Product Docs

- `docs/releases/acceptance-2026-06-15.md`
- `docs/TEST_MATRIX.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Changing the prompt or guardrail rules.
- Adding UI.
- Adding another provider.
- Committing `.env` or API keys.

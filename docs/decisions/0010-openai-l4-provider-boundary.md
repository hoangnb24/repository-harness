# 0010 OpenAI L4 Provider Boundary

Date: 2026-06-15

## Status

Accepted

## Context

VSF Data Profiler already has an optional L4 Senior Data Scientist narrative
path with fake-provider tests, deterministic fallback, and guardrails over
numbers, references, and causal wording. The next slice needs a real provider
without changing deterministic artifacts, sending raw CSV data, or making tests
depend on network access or API credentials.

## Decision

Add an `openai` implementation of the existing `NarrativeProvider` boundary.
The adapter calls the OpenAI Responses API only when `--use-llm` selects the
provider and `OPENAI_API_KEY` is configured. It sends a bounded JSON prompt
derived from existing structured artifacts and the narrative context, never raw
CSV rows or unbounded samples.

Use `.env` or environment variables for local configuration:

- `VSF_PROFILER_LLM_PROVIDER=openai`
- `OPENAI_API_KEY`
- `VSF_OPENAI_MODEL`
- `VSF_OPENAI_BASE_URL`
- `VSF_OPENAI_TIMEOUT_SECONDS`
- `VSF_OPENAI_MAX_OUTPUT_TOKENS`

Keep tests on fake providers and an injected fake HTTP transport. Do not add a
required OpenAI SDK dependency for this MVP adapter.

## Alternatives Considered

1. Add the OpenAI Python SDK as a required dependency. Rejected for now because
   the project can make one bounded Responses API call with the standard
   library and avoid changing offline install behavior.
2. Fail the run when `--llm-provider openai` lacks an API key. Rejected because
   the product contract requires deterministic fallback when provider config is
   missing.
3. Let provider output bypass guardrails. Rejected because deterministic
   artifacts must remain the source of truth for numbers, references, and
   non-causal wording.

## Consequences

Positive:

- Users can opt into a real L4 narrative provider.
- Default deterministic runs remain offline and unchanged.
- Tests still run without real API calls or secrets.

Tradeoffs:

- The adapter owns a small amount of HTTP response parsing code.
- Additional providers will need their own adapters and fake transports.

## Follow-Up

- Add more provider adapters only behind the same guarded narrative boundary.
- Consider optional SDK support later if the provider surface grows.

# AI Feature Integration

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Building a feature that calls an LLM (Claude / GPT / open-weights) or any other generative model. Covers prompt management, model selection, cost/latency budget, prompt-injection defence, eval/regression, and fallback strategy. Stack-agnostic — applies whatever provider was chosen in stack-selection.

## When To Run

- A story introduces a new AI-powered behavior (chat, generation, classification, extraction, agent).
- Migrating an AI feature between providers or model versions.
- Auditing an existing AI feature for cost, latency, or safety regression.

Skip when: the AI feature is purely a third-party SaaS embed (e.g. Intercom AI widget) with no prompt code in your repo.

## Prompt Management

Prompts are **code**, not data. Version them, review them, test them.

- **Location:** `<src>/ai/prompts/<feature>.<ext>` — colocate with the feature code, not in a global prompts folder. Easier to delete with the feature.
- **Format:** plain text or markdown. Use a templating layer (`mustache` / `f-strings` / `Handlebars`) for variables. NEVER concatenate user input with string `+` — that's how injection happens.
- **Versioning:** when you change a prompt that's already in production, save the OLD prompt with a `.vN.<ext>` suffix and keep at least the previous version. Diff matters for eval regression.
- **Commit citation:** prompt changes cite the same `US-NNN.REQ-MMM` token as the feature story.

Anti-pattern: storing prompts in a database, loading at runtime, edited by non-engineers. You lose code review, git blame, and rollback in one move. Use a feature flag + versioned prompt file instead.

## Model Selection Decision Shape

Treat each AI feature as a mini-decision (record in `docs/decisions/NNNN-ai-<feature>.md` if non-trivial):

| Item | Choice | Reason |
| --- | --- | --- |
| Provider | `<Anthropic / OpenAI / Google / OpenRouter / self-hosted>` | |
| Model | `<exact ID — e.g. claude-sonnet-4-6, gpt-4o-mini>` | |
| Mode | `<chat / completion / structured output / tool-use / batch>` | |
| Max tokens (in + out) | `<n>` | drives cost ceiling |
| Streaming | `<yes / no>` | drives UX choice |
| Tool / function calling | `<list of tool names, or none>` | |
| Temperature / top_p | `<values>` | |
| Fallback model | `<smaller / cheaper / alt-provider>` | for retry on rate limit |

Default heuristic for picking model:

- **Latency-sensitive UX path** (user waits) → Haiku-class / GPT-4o-mini.
- **Quality-sensitive batch path** (background, accuracy matters) → Sonnet / GPT-4o.
- **Highest-stakes reasoning** (legal, medical, financial) → Opus / GPT-4-Turbo + human-in-the-loop.

## Cost & Latency Budget

Per AI feature, capture in `docs/templates/high-risk-story/design.md § Performance Budget`:

| Metric | Budget | Measurement |
| --- | --- | --- |
| Cost per invocation | `<USD>` | provider dashboard or `tiktoken`-style estimator pre-call |
| P95 latency | `<ms>` | client-side timer or provider trace |
| Daily cost ceiling | `<USD>` | alert at 80%, hard-stop at 100% |
| Token usage per call | `<input + output>` | provider response metadata |

Wire a daily cost alert to the monitoring stack chosen in stack-selection. Surprise $5k bills come from runaway loops, not steady traffic — also alert on **call-rate anomalies**, not just total cost.

## Prompt-Injection Defence

User-controlled text reaching the prompt is an attack surface. Mitigations (defence-in-depth — do all that apply):

1. **Sanitize boundaries.** Per `docs/ARCHITECTURE.md § Parse-First Boundary Rule`, user input is a typed value before reaching the prompt builder. Strip control characters and prompt-delimiter sequences (`<|im_start|>`, `</system>`, `[INST]`).
2. **Separate instructions from data.** Use the provider's system-prompt or message-role split. Never inline user input into the instruction block.
3. **Output validation.** If the model returns JSON, parse + validate (zod / pydantic). If it returns code, sandbox + lint before executing. If it returns a tool call, validate args against the tool schema before invoking.
4. **Action gating.** High-impact tool calls (DB writes, payment ops, email send) require a confirmation step (UI or token-bearing API call), NEVER straight from the model output.
5. **PII redaction at logging.** Don't log raw prompts that contain user PII. Hash or truncate before writing to logs (per `docs/ARCHITECTURE.md § Observability Contract`).
6. **Rate limit per user.** Prevents both abuse and accidental cost blowups.

Reference: OWASP LLM Top 10 — at minimum cover LLM01 (injection), LLM02 (insecure output handling), LLM06 (sensitive info disclosure), LLM08 (excessive agency).

## Eval / Regression Suite

Plain unit tests don't catch model-output regressions. Maintain a small eval suite:

- **Location:** `<src>/ai/evals/<feature>.<ext>`.
- **Shape:** 10-50 input / expected-output pairs per feature. Hand-curated, not auto-generated.
- **Run:** on every prompt change + on model version bump. NOT on every commit (cost).
- **Pass criterion:** quantitative (exact match, regex, BLEU, embedding similarity above threshold) OR a smaller LLM-as-judge call with a strict rubric.
- **Report:** `plans/reports/eval-<feature>-<date>.md` — pass rate + regressions vs previous run.

When a regression appears: revert the prompt change OR widen the eval suite to cover the failing case before re-attempting.

## Fallback Strategy

Model APIs fail. Plan for it:

| Failure | Mitigation |
| --- | --- |
| Rate limit (429) | retry with exponential backoff + fallback model |
| Provider 5xx | retry once, then fallback model / provider |
| Timeout | bound at the latency budget; if exceeded, return cached or degraded response |
| Cost ceiling hit | hard-stop with user-facing "AI temporarily unavailable" message; alert oncall |
| Output validation fail | re-prompt with constrained instruction (1 retry max), then fall back to deterministic path |

Implement fallback as a thin **provider abstraction** layer, not provider-specific SDK calls scattered through the codebase. Easier to swap, easier to test.

## Audit Logging

AI calls are product behavior. Log per `docs/ARCHITECTURE.md § Observability Contract`:

- `action: ai_call`
- `feature: <name>`
- `model: <id>`
- `input_tokens`, `output_tokens`, `cost_usd`
- `duration_ms`
- `outcome: ok | rate_limit | provider_error | validation_fail | fallback`
- `user_id` (when known) for per-user attribution
- Do NOT log raw prompt or completion in the application log. If needed for debugging, write to a separate, retention-limited "prompt log" sink with PII scrubbing.

## Cross-Tier Behavior

| Lane | AI playbook application |
| --- | --- |
| Tiny | Optional — most tiny work doesn't add AI features. |
| Normal | Required for new AI feature: prompt file + cost budget + audit log. Eval suite optional. |
| High-Risk | Required everywhere: prompt file + cost budget + injection defence + eval suite + fallback strategy + per-feature decision doc + audit log. |

## Variant Section

(Append a Variant block here when this playbook fails or partially works.)

## Related

- `docs/templates/decisions/stack-selection.md` § External Providers — picks the AI provider before this playbook runs.
- `docs/playbooks/code-review-scoring.md` — security dimension scores prompt-injection defence.
- `docs/templates/high-risk-story/design.md § Performance Budget` — cost/latency budget lives there for high-risk stories.
- `docs/ARCHITECTURE.md § Parse-First Boundary Rule` — sanitisation lives at the boundary.
- `docs/ARCHITECTURE.md § Observability Contract` — log line shape.
- `docs/playbooks/payment-integration.md` — sibling provider-integration playbook with the same shape.

## Tooling Hints (Optional)

These are convenience wrappers, NOT required. Per `docs/HARNESS.md § Independence Principle`:

- `/ck:ai-multimodal` — multi-modal analysis (image/audio/video).
- `/ck:google-adk-python` — Google Agent Development Kit projects.
- `/ck:claude-api` — Anthropic SDK + prompt caching patterns.

Fallback: call provider SDK or HTTP API directly.

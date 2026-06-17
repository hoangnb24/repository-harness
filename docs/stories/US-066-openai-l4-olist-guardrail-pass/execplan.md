# Exec Plan

## Goal

Make the real OpenAI L4 narrative pass guardrails on the Olist demo without
fallback, without leaking secrets/raw CSV data, and without weakening
guardrails.

## Scope

In scope:

- L4 prompt and provider payload tuning.
- Additive narrative context or deterministic draft evidence.
- Guardrail parsing fixes that preserve strictness.
- Tests for fake provider, fallback, and OpenAI payload safety.
- Real Olist OpenAI smoke validation.

Out of scope:

- Core profiler artifact or schema changes.
- Mandatory LLM usage.
- New external LLM providers.
- Hosted/backend deployment changes.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Existing behavior.
- Weak proof.

Hard gates:

- External provider behavior.
- Secret/raw-data leakage prevention.
- Guardrail validation must not be weakened.

Lane: high-risk.

## Work Phases

1. Discovery: inspect current L4 code, tests, report surfaces, and prior smoke
   evidence.
2. Reproduction: identify current real-provider guardrail failure evidence from
   existing artifacts or a controlled smoke.
3. Implementation: tune prompt/context/guardrail parsing with additive
   contracts only.
4. Focused verification: run L4 tests and Ruff on L4 files.
5. Full verification: run full tests, Ruff, demo, real OpenAI Olist smoke,
   verifier, secret scan, and Harness checks.
6. Harness update: update story evidence, matrix, and trace.

## Stop Conditions

Pause for human confirmation if:

- OpenAI API/auth/network fails independently of code.
- Passing would require weakening guardrails.
- Raw CSV or secret exposure would be needed.
- Existing artifact or CLI contracts would need breaking changes.

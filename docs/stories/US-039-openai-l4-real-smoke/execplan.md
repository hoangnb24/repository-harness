# Exec Plan

## Goal

Prove the real OpenAI L4 smoke path on the existing demo dataset and record
evidence without changing product behavior or exposing secrets.

## Scope

In scope:

- Existing demo dataset.
- Baseline default demo run.
- Separate OpenAI L4 run.
- Artifact, guardrail, log/privacy, and deterministic-hash verification.
- Acceptance/release documentation.

Out of scope:

- Prompt rewrites.
- UI or web runner bridge work.
- Additional providers.
- Committing `.env` or provider credentials.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Public contracts.
- Existing behavior.

Hard gates:

- No key or secret marker in output logs/events/reports/L4/guardrail artifacts.
- No exact raw CSV data row in those outputs.
- Baseline deterministic core artifact hashes unchanged after OpenAI run.
- OpenAI run deterministic core artifacts match baseline.
- Guardrail status is `passed` or `fallback_used` with a clear reason.

## Work Phases

1. Discovery.
2. Intake and story setup.
3. Baseline run and manifest capture.
4. Real OpenAI smoke run.
5. Artifact/privacy/hash verification.
6. Acceptance evidence update and Harness trace.

## Stop Conditions

Pause for human confirmation if:

- No local OpenAI key is configured.
- The smoke would require printing or committing the API key.
- The provider path requires weakening guardrails.
- The run mutates deterministic artifacts unexpectedly.

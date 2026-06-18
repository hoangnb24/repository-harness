# Exec Plan

## Goal

Add a real optional OpenAI provider for the guarded L4 narrative path while
preserving deterministic default behavior, no-raw-CSV prompt boundaries, and
fake-provider tests.

## Scope

In scope:

- OpenAI provider adapter behind `NarrativeProvider`.
- `.env.example` for local API key configuration.
- Missing-key deterministic fallback.
- Mocked provider tests with no real API calls.
- Product, architecture, matrix, decision, and story docs.

Out of scope:

- Real API validation in CI.
- Other LLM providers.
- Report template redesign.
- Raw CSV or sample-row prompting.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Public CLI contract.
- Existing deterministic behavior.

Hard gates:

- Focused L4 tests pass.
- Full pytest passes.
- Ruff passes.
- `make demo-small` passes without L4 artifacts.
- Fake LLM run writes passed guardrail artifacts.
- Missing-key OpenAI run writes deterministic fallback artifacts.
- `story verify US-038` and Harness audit pass.

## Work Phases

1. Discovery: read Harness docs, product docs, L4 implementation, and OpenAI
   Responses API docs.
2. Design: record high-risk intake, story, and provider-boundary decision.
3. Validation planning: add fake-transport tests and missing-key fallback proof.
4. Implementation: add provider, `.env` loader, docs, and story packet.
5. Verification: run focused tests, full tests, Ruff, demos, story verify, and
   audit.
6. Harness update: update matrix, story proof, and trace.

## Stop Conditions

Pause for human confirmation if:

- Provider setup would require sending raw CSV or sample rows.
- Deterministic artifact names need to change.
- Tests would need real OpenAI credentials or network calls.
- Guardrail requirements need to be weakened.

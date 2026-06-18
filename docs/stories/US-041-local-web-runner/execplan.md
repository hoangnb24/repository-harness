# Exec Plan

## Goal

Add a local web runner that lets users upload DBML/CSV/rules in the browser,
run the existing Python DuckDB pipeline, stream canonical runtime progress, and
inspect generated artifacts.

## Scope

In scope:

- `vsf-profiler web` command bound to `127.0.0.1`.
- Upload mode for demo/small-medium files.
- Backend job execution via `run_pipeline()`.
- Server-sent runtime events from `run_events.jsonl`.
- Artifact listing and serving without renaming artifacts.
- UI runner panel and docs.

Out of scope:

- Large-data local path mode.
- Hosted backend.
- JS profiler port.
- New LLM behavior.
- Artifact contract changes.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Cross-platform.
- Weak proof.

Hard gates:

- Backend binds only `127.0.0.1`.
- Tests prove uploaded demo inputs produce canonical artifacts.
- UI references `run_events.jsonl`/`run_summary.json` rather than inferred
  stage state.
- Existing deterministic artifact names are unchanged.

## Work Phases

1. Discovery.
2. Design and durable decision.
3. Backend implementation.
4. UI implementation.
5. Tests and docs.
6. Browser verification.
7. Harness update.

## Stop Conditions

Pause for human confirmation if:

- The implementation would need to weaken local-only binding.
- The Python pipeline must be forked or ported to JavaScript.
- Existing artifact names must change.
- Validation cannot prove uploaded runs use the canonical pipeline.

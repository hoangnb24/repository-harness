# Exec Plan

## Goal

Produce executable benchmark evidence that VSF Data Profiler handles larger
multi-table CSV/Postgres-style datasets through the existing DuckDB pipeline
without full pandas CSV materialization.

## Scope

In scope:

- Deterministic large synthetic relational dataset generator.
- `scripts/benchmark_large_dataset.py`.
- `performance_guard_report.json`.
- CI-safe small benchmark and optional larger local benchmark command.
- Tests and docs for benchmark output and materialization guards.

Out of scope:

- Distributed compute.
- Hosted benchmark dashboard.
- Exact machine-independent performance SLA.
- New connector types.
- Rewriting profiler logic.

## Risk Classification

Risk flags:

- Existing behavior: benchmark touches pipeline validation and release checks.
- Weak proof: performance claims require concrete evidence.
- Multi-domain: generator, pipeline, package, audit, docs, and Harness records.
- Public contracts: new script, make targets, and benchmark report contract.

Hard gates:

- Benchmark and observability claims require detailed trace and durable proof.

## Work Phases

1. Discovery of existing memory guards, pipeline limits, package/audit commands.
2. Story and decision records.
3. Generator and benchmark implementation.
4. Tests for deterministic generation, CI-safe benchmark, and guard report.
5. Docs and validation matrix updates.
6. Full validation, Harness story/decision verify, trace, and audit.

## Stop Conditions

Pause for human confirmation if:

- Supporting the benchmark requires a second profiler engine.
- Existing artifact names or demo behavior would need to change.
- Validation would require weakening existing memory guards.
- A local benchmark cannot complete under conservative CI-safe settings.

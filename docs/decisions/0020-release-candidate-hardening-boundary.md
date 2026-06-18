# 0020 Release Candidate Hardening Boundary

Date: 2026-06-16

## Status

Accepted

## Context

VSF Data Profiler has accumulated the v0.2 feature set across CLI, web runner,
Postgres, L4 guardrails, lineage graphs, dashboard graphs, and export packages.
Before adding more product surface, the project needs a reliable release
candidate workflow that others can run locally and diagnose when prerequisites
are missing.

## Decision

Add release-hardening surfaces only:

- `vsf-profiler doctor` for environment diagnostics;
- `scripts/verify_vsf_artifacts.py` for final artifact/package audits;
- `make demo-full` for one-command local RC demo;
- `docs/releases/v0.2-rc.md` for exact commands and expected outputs.

The doctor must not print secret values. Optional capabilities such as Postgres,
OpenAI, Node, and Playwright report `ok`, `missing`, or `skipped` without
blocking the core demo unless the optional check is explicitly present and
fails. The artifact audit validates existing outputs; it does not create new
profiling facts.

## Alternatives Considered

1. Start new connector/PDF/benchmark work immediately. Rejected because the
   current priority is making the existing feature set runnable by others.
2. Make Playwright/Postgres required for the full demo. Rejected because the
   local RC path should work on machines without optional services.
3. Print raw environment values for easier debugging. Rejected because release
   diagnostics must preserve the established redaction boundary.

## Consequences

Positive:

- Reviewers get a single local command and exact expected artifacts.
- Missing optional capabilities are visible without being noisy failures.
- Release audits check raw-data and secret boundaries after package export.

Tradeoffs:

- `make demo-full` remains a smoke workflow, not a performance benchmark.
- Optional browser proof depends on the local Node/Playwright installation.

## Follow-Up

- Revisit large-data benchmarks after v0.2 RC is stable.

## Verification

```text
.venv/bin/pytest -q tests/test_doctor_and_artifact_audit.py tests/test_export_package.py tests/test_demo_small.py
make demo-full
```

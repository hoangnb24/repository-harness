# Overview

## Current Behavior

The VSF Data Profiler has the v0.2 feature set: CSV/DBML profiling, web-runner
dashboard, Postgres connector, L4 guardrails, lineage/relationship graphs, and
offline export packages. The demo and validation commands exist, but there is
not yet one release-candidate command that runs the local demo, optional browser
checks, package export, and final artifact audit with clear diagnostics.

## Target Behavior

The repo exposes a reliable v0.2 release-candidate path:

- `make demo-full` runs the local demo, doctor checks, package export, artifact
  audit, optional Playwright dashboard E2E, and prints key output paths.
- `vsf-profiler doctor` reports required and optional environment readiness
  without printing secrets.
- `scripts/verify_vsf_artifacts.py` audits canonical run/package artifacts,
  raw CSV exclusions, secret-like strings, and deterministic artifact names.
- `docs/releases/v0.2-rc.md` tells reviewers the exact commands and expected
  outputs.

## Affected Users

- Local evaluator trying the release candidate.
- Maintainer preparing a demo package.
- Agent or reviewer validating final artifact integrity.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/releases/v0.2-rc.md`

## Non-Goals

- No new product features.
- No hosted deployment.
- No new database connectors.
- No PDF generation.
- No performance benchmark beyond smoke timing.

# Overview

## Current Behavior

VSF Data Profiler has the v0.2 product capabilities in place, including the
US-050 hardening base and US-052 MySQL/PDF additions. Some release-facing docs
still used earlier release wording, and the static Vercel deployment boundary
was not stated consistently alongside the local web runner.

## Target Behavior

US-053 performs a release-freeze cleanup without adding product behavior:

- README, product, architecture, demo, and release docs describe v0.2 as a
  local release candidate instead of an earlier demo framing.
- Vercel is documented as a static preflight surface only.
- Full Python/DuckDB profiling jobs remain local-only through CLI or
  `vsf-profiler web` on `127.0.0.1`.
- Version metadata follows the v0.2 RC convention.
- Generated local files are ignored or cleaned without deleting ambiguous
  source/docs/tests.
- Harness story, decision, matrix, and final evidence record the release
  freeze.

## Affected Users

- Local users validating the v0.2 RC demo path.
- Reviewers checking whether the hosted static UI is a full backend.
- Maintainers preparing a clean release candidate handoff.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/demo/vsf-data-profiler.md`
- `docs/releases/v0.2-rc.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0023-vercel-static-local-runner-release-boundary.md`

## Non-Goals

- No profiler, dashboard, connector, PDF, LLM, or artifact-contract features.
- No hosted backend or production deployment architecture.
- No artifact renames.
- No deletion of ambiguous user-created source, docs, or tests.

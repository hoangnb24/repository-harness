# 0019 Export Package Boundary

Date: 2026-06-16

## Status

Accepted

## Context

VSF output directories contain deterministic reports, JSON artifacts, runtime
traces, chart specs, and bounded sample evidence. Users need an offline package
for demo submission and stakeholder handoff. That package changes the public
CLI surface and creates a new artifact inventory, so the raw data and secret
boundaries need a durable decision.

## Decision

Add `vsf-profiler package` as a separate CLI command that packages an existing
run output directory. The command copies only generated artifacts and bounded
sample files into a self-contained package directory, writes
`export_manifest.json`, renders an offline `index.html`, and can optionally
create a deterministic zip archive.

The package command must not copy raw source CSV directories, hidden connector
extracts, temp files, or package outputs from previous runs. It must not rerun
profiling, infer new findings, call external services, or require the local web
runner. A redaction scan over included text artifacts must pass before the
manifest is accepted.

## Alternatives Considered

1. Zip the entire output directory. Rejected because output directories may sit
   near raw inputs or temp connector extracts and need explicit allow-listing.
2. Generate packages during every profiler run. Rejected because packages are a
   handoff operation and should not alter the existing deterministic run
   contract by default.
3. Reuse the web runner dashboard as the package. Rejected because the package
   must be reviewable offline without a running server.

## Consequences

Positive:

- Users can hand off a complete generated-analysis package without raw source
  data.
- The manifest gives reviewers checksums and source run metadata.
- Existing profiling artifacts and web runner behavior remain unchanged.

Tradeoffs:

- The offline index is a static navigator, not an interactive dashboard.
- Package completeness depends on the source run artifacts already present.

## Follow-Up

- Consider richer rendered chart images later if chart specs are not enough for
  nontechnical recipients.

## Verification

```text
.venv/bin/pytest -q tests/test_export_package.py tests/test_demo_small.py
node --check web/app.js
```

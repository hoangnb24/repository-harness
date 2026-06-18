# Overview

## Current Behavior

The local web runner can start upload-mode and local-path-mode jobs, stream
runtime events, and list generated artifact links. Static `report.html` and
`report.md` include a deterministic Visual Summary built from chart specs, but
the web runner UI does not provide an interactive dashboard after a run.

## Target Behavior

After a web-runner job completes, the UI shows an interactive Dashboard section
that fetches generated artifacts by job artifact URLs and renders existing chart
specs plus machine artifacts. Users can filter by severity, issue type, and
table, then click chart items to inspect matching issues, affected
tables/columns, counts/rates, artifact links, and bounded sample links when
available.

Upload mode and local path mode both populate the same dashboard without
rerunning the profiler.

## Affected Users

- Local users reviewing run output in the browser.
- Maintainers validating that dashboard facts come from canonical artifacts.
- Demo users who need a no-build, no-internet dashboard.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0013-web-runner-dashboard-boundary.md`

## Non-Goals

- No JavaScript implementation of profiling, validation, verdict, relationship,
  or LLM logic.
- No raw CSV file reads after a run.
- No CDN, frontend build step, hosted SaaS, auth, database connectors, or full
  lineage.
- No artifact name or CLI output contract changes.
- No changes to the static report Visual Summary beyond documentation.

# Overview

## Current Behavior

VSF profiling runs produce a deterministic output directory with JSON
artifacts, bounded sample CSV files, runtime traces, and static Markdown/HTML
reports. Users can review that output in place or through the local web runner,
but there is no command that turns an existing run directory into a
self-contained handoff package.

## Target Behavior

Users can run `vsf-profiler package --input <run-output> --output <package-dir>`
to create a self-contained analysis package. The package includes canonical
artifacts, chart specs, reports, runtime files, bounded sample evidence, an
`export_manifest.json` with SHA-256 checksums and source run metadata, and an
offline `index.html` entrypoint. Raw source CSV files and connector temporary
extracts remain excluded.

## Affected Users

- Local data scientist exporting a profiling run for review.
- Analyst preparing a demo submission without a running backend.
- Stakeholder receiving an offline handoff package.
- Agent or reviewer validating artifact completeness and redaction.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- No hosted sharing service.
- No authentication or permissions layer.
- No PDF generation.
- No report editing inside the package.
- No profiling rerun from the package.

# Exec Plan

## Goal

Add a CLI package command and export artifacts that make an existing VSF output
directory self-contained for offline review while preserving raw-data and
secret boundaries.

## Scope

In scope:

- `vsf-profiler package --input --output [--zip]`.
- `export_manifest.json` with checksums, source run metadata, redaction status,
  and package file inventory.
- Offline `index.html` entrypoint.
- Inclusion of canonical artifacts, chart specs, graph artifacts, reports,
  runtime files, optional connector/L4 artifacts, and bounded sample CSVs.
- Exclusion of raw source CSVs and connector temporary extracts.
- Tests and docs.

Out of scope:

- Hosted sharing service.
- Authentication.
- PDF generation.
- Editing reports in the package.
- Re-running profiling from the package.

## Risk Classification

Risk flags:

- Audit/security: package contents must not leak secrets or raw data.
- Public contracts: new CLI command and manifest contract.
- Existing behavior: existing pipeline artifacts must remain unchanged.
- Cross-platform: offline directory and zip behavior.
- Multi-domain: CLI, docs, tests, and package HTML entrypoint.

Hard gates:

- Audit/security.

## Work Phases

1. Discovery.
2. Harness story and decision.
3. Package module and CLI command.
4. Manifest and static index rendering.
5. Tests for inclusion, exclusion, checksums, redaction, and zip.
6. Docs and validation.

## Stop Conditions

Pause for human confirmation if:

- Packaging requires copying raw source CSV files.
- Existing artifact names or `run_pipeline()` behavior would need to change.
- Redaction validation would need to be weakened.
- A hosted service, auth layer, or external rendering dependency becomes
  necessary.

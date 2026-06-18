# Exec Plan

## Goal

Add an interactive artifact dashboard to the local VSF web runner that renders
existing chart specs and machine artifacts after upload-mode and local-path-mode
jobs.

## Scope

In scope:

- Dashboard artifact discovery endpoint.
- Client-side artifact fetching by protected artifact URLs.
- SVG/CSS panels for verdict risk, issue severity, issue type, missingness,
  relationship FK health, and influence top features.
- Severity, issue type, and table filters.
- Drilldown details for chart selections and matching issue rows.
- Static UI and backend tests.
- Product docs, story packet, durable decision, and test matrix update.

Out of scope:

- New profiler semantics.
- Raw CSV dashboard reads.
- Frontend build tooling or CDN dependencies.
- Hosted SaaS, auth, database connectors, or lineage.
- Static report redesign.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Cross-platform.
- Weak proof.

Hard gates:

- Dashboard consumes generated artifacts only.
- Upload and local path modes keep working.
- Server remains local-only on `127.0.0.1`.
- Existing artifact names and CLI output contracts remain unchanged.
- No raw CSV files are fetched or embedded by the dashboard.

## Work Phases

1. Discovery and Harness intake.
2. Story and decision records.
3. Backend artifact discovery endpoint plus tests.
4. UI dashboard markup, state, renderers, filters, and drilldown.
5. Focused tests and JS syntax check.
6. Full validation and local smoke for upload/path jobs.
7. Harness proof update and audit.

## Stop Conditions

Pause for human confirmation if:

- Existing artifact data is insufficient and profiler semantics would need to
  change.
- A build system, CDN, or raw CSV dashboard read becomes necessary.
- Existing artifact names or CLI output structure would need to break.
- Scope expands into hosted multi-user, auth, connector, or lineage work.

# Exec Plan

## Goal

Add an artifact-driven interactive lineage and relationship graph view to the
local web-runner dashboard while preserving existing pipeline behavior and
artifact contracts.

## Scope

In scope:

- Render `lineage_graph.json` as an SVG graph in the web dashboard.
- Render `relationship_graph.json` as a focused FK graph.
- Add graph mode and scope controls.
- Add node click drilldown with metadata, related issues, and artifact links.
- Add static UI and Playwright E2E coverage.
- Update product docs, story evidence, and durable Harness records.

Out of scope:

- Raw CSV dashboard reads.
- JavaScript profiling/validation/lineage logic.
- Backend artifact contract changes.
- External graph libraries, CDNs, auth, hosting, or connector expansion.

## Risk Classification

Risk flags:

- Public contracts: browser dashboard behavior changes.
- Cross-platform: local browser UI and Playwright proof.
- Existing behavior: upload/local path/Postgres runner artifacts must remain
  compatible.
- Audit/security: dashboard must not fetch raw CSVs or leak connector secrets.
- Multi-domain: dashboard UI, docs, and Harness proof all change.

Hard gates:

- Audit/security.

## Work Phases

1. Discovery of current dashboard, lineage, relationship, and E2E surfaces.
2. Harness story and decision updates.
3. UI structure and renderer implementation.
4. Static and E2E test updates.
5. Focused and full verification.
6. Trace, matrix, and audit update.

## Stop Conditions

Pause for human confirmation if:

- Rendering requires a frontend build system, CDN, or heavyweight dependency.
- Graph data is insufficient and would require changing profiler semantics.
- Artifact names, runner routes, or output directory structure would need to
  break.
- Browser graph code would need to fetch raw CSV inputs.

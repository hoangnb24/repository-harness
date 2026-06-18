# Overview

## Current Behavior

The Postgres connector has unit/fake-connector coverage and a small optional
local Postgres test. That optional test proves basic introspection and FK
metadata when `VSF_POSTGRES_TEST_URL` is configured, but it does not exercise
the full acceptance path across DBML and non-DBML modes, lineage, dashboard
artifact discovery, chunked extraction, and secret leak checks.

## Target Behavior

The repo provides a real Postgres acceptance smoke that creates and drops a
disposable schema in a local test database, runs the existing VSF Python/DuckDB
pipeline in two modes, and verifies the full generated artifact surface:

- Postgres introspection without DBML.
- Postgres with DBML supplied.

The smoke remains optional. It skips with an explicit message when no
`VSF_POSTGRES_TEST_URL` is configured and no Harness-registered Postgres or
Docker capability is present.

## Affected Users

- Maintainers validating the Postgres connector before release.
- CLI users who need confidence that connector metadata, lineage, reports, and
  runtime artifacts work against a live database.
- Agents preserving the local-only and secret-redaction boundaries.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/stories/US-047-real-postgres-connector-acceptance-smoke/validation.md`

## Non-Goals

- No new database connectors.
- No hosted deployment.
- No external lineage catalog publishing.
- No large benchmark or performance suite.

# 0017 Real Postgres Acceptance Smoke Boundary

Date: 2026-06-16

## Status

Accepted

## Context

The Postgres connector has fake connector coverage and an optional minimal live
database test. US-047 raises the validation bar: a real database smoke must
prove that connector metadata, schema introspection, optional DBML, lineage,
reports, runtime artifacts, dashboard artifact discovery, chunked extraction,
cleanup, and redaction work together.

This introduces external-system validation and secret-handling proof, so the
acceptance boundary needs a durable decision.

## Decision

Add a pytest-based acceptance smoke that runs only when `VSF_POSTGRES_TEST_URL`
is configured. The test creates a unique disposable schema, populates tiny
relational tables, runs the existing `PostgresConnector` through the existing
Python/DuckDB pipeline in introspection and DBML modes, verifies generated
artifacts and web-runner artifact discovery, checks cleanup, and scans outputs
for secret leakage.

When no URL is configured, the smoke skips explicitly. Docker remains an
operator convenience documented for local setup, not a mandatory test runner
dependency unless a future Harness tool capability registers it.

## Alternatives Considered

1. Always start Docker from tests. Rejected because Docker is not registered as
   a present Harness capability here and availability should not be assumed.
2. Require a hosted Postgres service. Rejected because the product and harness
   remain local-first.
3. Keep only fake connector tests. Rejected because fake tests cannot prove
   psycopg introspection, chunked extraction, and live connection redaction.

## Consequences

Positive:

- Maintainers get a repeatable real connector acceptance path.
- Default CI/developer runs remain green without Postgres.
- Redaction proof covers the live connector artifact surface.

Tradeoffs:

- Environments without Postgres prove only the skip path until a local database
  is provided.
- Docker orchestration is documented but not automatically invoked by default.

## Follow-Up

- Register a `docker` or `postgres` Harness tool capability if this repo starts
  running disposable database smoke tests automatically in CI.

## Verification

```text
.venv/bin/pytest -q tests/test_postgres_acceptance.py
```

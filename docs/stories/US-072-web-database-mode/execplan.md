# Exec Plan

## Goal

Add first-class Postgres/MySQL database mode to the local web runner while
preserving the local-only credential boundary, existing connector pipeline, and
generated artifact contracts.

## Scope

In scope:

- `/api/database-jobs` backend endpoint.
- Web-runner `start_database_job` orchestration.
- UI Database mode controls for Postgres/MySQL, schema, tables, target, chunk
  rows, rules path, and shared L4 report toggle.
- Tests for redaction, endpoint validation, static UI markers, and Playwright
  form behavior.
- Product docs, story evidence, and durable decision record.

Out of scope:

- Hosted database connectivity.
- Production database mutation or repair.
- New connector engines beyond existing Postgres and MySQL/MariaDB.
- Persisting raw full-table CSV extracts after the run.

## Risk Classification

Risk flags:

- Audit/security: connection URLs contain credentials.
- External systems: Postgres/MySQL database connections.
- Public contracts: new local HTTP endpoint and request shape.
- Existing behavior: shared web runner and artifact dashboard.
- Cross-platform: browser form and local backend behavior.

Hard gates:

- Audit/security.
- External provider behavior.

## Work Phases

1. Discovery of existing web runner and connector boundaries.
2. Durable story and decision record.
3. Backend endpoint and job orchestration.
4. UI controls and responsive polish.
5. Unit/static/E2E validation.
6. Product docs, story evidence, and trace.

## Stop Conditions

Pause for human confirmation if:

- The implementation needs to persist raw database extracts after completion.
- A real database credential must be stored in docs, tests, screenshots, or
  committed fixtures.
- The existing connector redaction guarantee needs to be weakened.

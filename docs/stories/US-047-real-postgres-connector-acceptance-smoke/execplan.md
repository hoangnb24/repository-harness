# Exec Plan

## Goal

Add a real Postgres acceptance smoke path that proves live connector runs work
end-to-end in introspection and DBML modes without leaking secrets.

## Scope

In scope:

- Disposable Postgres fixture schema.
- Two smoke modes: introspection without DBML and DBML-supplied connector run.
- Required artifact checks for connector metadata, schema diagnostics,
  evaluation, relationship graph, lineage graph, verdict, charts, reports, and
  runtime files.
- Cleanup checks for connector extracts.
- Redaction checks across artifacts, reports, events, dashboard payloads, and
  runtime logs.
- Documentation for `VSF_POSTGRES_TEST_URL` and optional Docker setup.
- Clean skip when no test database is available.

Out of scope:

- MySQL, SQL Server, warehouses, or other connectors.
- Hosted runners or web credential entry.
- External lineage catalog publishing.
- Large benchmark or performance suite.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Data model.
- Public contracts.
- Existing behavior.
- Weak proof.

Hard gates:

- The smoke must never mutate non-disposable schemas.
- The full connection URL, password, token, and secret-like strings must not
  appear in generated outputs.
- Lack of local Postgres/Docker must remain a skip, not a failure.

## Work Phases

1. Intake, story, and validation boundary.
2. Disposable fixture helper.
3. Acceptance test for introspection and DBML modes.
4. Web/dashboard artifact discovery assertions.
5. Documentation and test matrix update.
6. Focused/full validation and Harness trace.

## Stop Conditions

Pause for human confirmation if:

- The smoke would require mutating a persistent or shared schema.
- Existing connector/artifact names would need to break.
- Secret redaction cannot be proven.
- The test cannot skip cleanly without local infrastructure.

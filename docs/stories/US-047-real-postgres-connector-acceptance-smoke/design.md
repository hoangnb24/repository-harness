# Design

## Domain Model

The smoke uses the existing Postgres connector boundary:

- `PostgresConnector` adapts a live database into `Schema` and `CsvCatalog`.
- `connector_metadata.json` records redacted source metadata.
- Existing pipeline services produce profile, issue, schema, relationship,
  lineage, verdict, chart, report, and runtime artifacts.

The fixture schema has customers, orders, and order reviews with PK/FK
relationships, nullable fields, duplicate/quality issues, and more rows than
the smoke chunk size so extraction exercises multiple fetches.

## Application Flow

1. Resolve a test Postgres URL from `VSF_POSTGRES_TEST_URL`.
2. If no URL is present, skip with an explicit message. The optional Docker
   recipe in docs can be used to create a local database and set the URL.
3. Create a unique disposable schema.
4. Create relational tables and insert deterministic rows.
5. Run the pipeline once with connector introspection and no DBML.
6. Run the pipeline again with DBML supplied and the same connector table
   selection.
7. Verify required artifacts, reports, lineage, dashboard artifact discovery,
   extracted-temp cleanup, issue types, and redaction.
8. Drop the disposable schema.

## Interface Contract

No CLI contract changes are required. The smoke uses existing options and APIs:

- `VSF_POSTGRES_TEST_URL`
- `--postgres-url-env`
- `--postgres-schema`
- `--postgres-tables`
- `--postgres-chunk-rows`
- optional `--dbml`

## Data Model

The fixture creates a temporary schema named `vsf_accept_<uuid>` with:

- `customers(customer_id PK, email unique nullable, customer_state nullable)`;
- `orders(order_id PK, customer_id FK, order_total numeric nullable,
  delivered_at timestamp nullable)`;
- `order_reviews(review_id PK, order_id FK, review_score int nullable)`.

Rows include duplicate emails, nullable fields, and enough records to force
chunked extraction with a small chunk size.

## UI / Platform Impact

The local web runner does not accept database credentials in this slice.
Instead, the smoke verifies that a completed connector output directory is
discoverable through existing `WebRunStore` artifact and dashboard payload
logic.

## Observability

The smoke checks `run.log`, `run_events.jsonl`, `run_summary.json`, reports,
`connector_metadata.json`, `lineage_graph.json`, and dashboard payloads for
secret leakage. Temporary connector extracts must be removed after each run.

## Alternatives Considered

1. Always start Docker from pytest. Rejected because the Harness registry has
   no present Docker capability in this environment and clean skip behavior is
   required.
2. Keep only the existing two-row Postgres integration. Rejected because it
   does not prove the full acceptance artifact/redaction path.
3. Add web UI credential entry. Rejected because web credential handling is out
   of scope for this smoke.

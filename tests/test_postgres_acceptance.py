import json
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from vsf_profiler.cli import run_pipeline
from vsf_profiler.connectors import PostgresConnector
from vsf_profiler.web_runner import WebRunJob, WebRunStore


REQUIRED_ARTIFACTS = {
    "profile_summary.json",
    "issues.json",
    "connector_metadata.json",
    "schema_parse_report.json",
    "schema_evaluation.json",
    "relationship_graph.json",
    "lineage_graph.json",
    "dataset_verdict.json",
    "table_assessments.json",
    "influence.json",
    "run.log",
    "run_events.jsonl",
    "run_summary.json",
    "report.md",
    "report.html",
}
REQUIRED_CHARTS = {
    "dataset_verdict_risk_summary.json",
    "issue_counts_by_severity.json",
    "issue_counts_by_type.json",
    "missingness_by_table.json",
    "missingness_top_columns.json",
    "relationship_fk_health.json",
}


def test_real_postgres_acceptance_smoke_introspection_and_dbml_modes(tmp_path):
    url = _postgres_url_or_skip()
    psycopg = pytest.importorskip(
        "psycopg",
        reason="Real Postgres smoke requires `python -m pip install -e .[postgres]`.",
    )
    schema_name = f"vsf_accept_{uuid.uuid4().hex[:8]}"
    rules_path = _write_rules(tmp_path / "rules.yaml")
    dbml_path = _write_dbml(tmp_path / "schema.dbml")

    _create_fixture(psycopg, url, schema_name)
    try:
        introspection_out = tmp_path / "introspection"
        dbml_out = tmp_path / "dbml"

        _run_postgres_pipeline(
            url=url,
            schema_name=schema_name,
            out_dir=introspection_out,
            dbml_path=None,
            rules_path=rules_path,
        )
        _run_postgres_pipeline(
            url=url,
            schema_name=schema_name,
            out_dir=dbml_out,
            dbml_path=dbml_path,
            rules_path=rules_path,
        )

        _assert_acceptance_outputs(
            out_dir=introspection_out,
            url=url,
            schema_name=schema_name,
            expected_parse_status="generated_from_connector",
            expected_issue_types={"FOREIGN_KEY_NULL", "VALUE_OUT_OF_RANGE"},
        )
        _assert_acceptance_outputs(
            out_dir=dbml_out,
            url=url,
            schema_name=schema_name,
            expected_parse_status="parsed",
            expected_issue_types={
                "FOREIGN_KEY_NULL",
                "VALUE_OUT_OF_RANGE",
                "UNIQUE_DUPLICATE",
                "REQUIRED_FIELD_NULL",
            },
        )
    finally:
        _drop_fixture(psycopg, url, schema_name)


def _postgres_url_or_skip() -> str:
    url = os.environ.get("VSF_POSTGRES_TEST_URL", "").strip()
    if not url:
        pytest.skip(
            "VSF_POSTGRES_TEST_URL is not configured and no Harness-present Postgres/Docker "
            "fixture is wired for this run; real Postgres smoke skipped. Use the README "
            "Docker recipe or point VSF_POSTGRES_TEST_URL at a disposable local database."
        )
    return url


def _create_fixture(psycopg, url: str, schema_name: str) -> None:
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
            cur.execute(
                f'''
                CREATE TABLE "{schema_name}"."customers" (
                  customer_id text PRIMARY KEY,
                  email text,
                  customer_state text
                )
                '''
            )
            cur.execute(
                f'''
                CREATE TABLE "{schema_name}"."orders" (
                  order_id text PRIMARY KEY,
                  customer_id text REFERENCES "{schema_name}"."customers"(customer_id),
                  order_total numeric,
                  delivered_at timestamp
                )
                '''
            )
            cur.execute(
                f'''
                CREATE TABLE "{schema_name}"."order_reviews" (
                  review_id text PRIMARY KEY,
                  order_id text REFERENCES "{schema_name}"."orders"(order_id),
                  review_score integer
                )
                '''
            )
            cur.execute(
                f'''
                INSERT INTO "{schema_name}"."customers" VALUES
                  ('C001', 'duplicate@example.test', 'NY'),
                  ('C002', 'duplicate@example.test', NULL),
                  ('C003', 'third@example.test', 'unknown'),
                  ('C004', 'fourth@example.test', 'CA')
                '''
            )
            cur.execute(
                f'''
                INSERT INTO "{schema_name}"."orders" VALUES
                  ('O001', 'C001', 10.00, '2026-01-01 10:00:00'),
                  ('O002', 'C002', -5.00, '2026-01-02 10:00:00'),
                  ('O003', NULL, 20.00, NULL),
                  ('O004', 'C003', 30.00, '2026-01-04 10:00:00'),
                  ('O005', 'C004', 40.00, '2026-01-05 10:00:00')
                '''
            )
            cur.execute(
                f'''
                INSERT INTO "{schema_name}"."order_reviews" VALUES
                  ('R001', 'O001', 5),
                  ('R002', 'O002', 6),
                  ('R003', NULL, 3),
                  ('R004', 'O004', 0),
                  ('R005', 'O005', NULL)
                '''
            )
        conn.commit()


def _drop_fixture(psycopg, url: str, schema_name: str) -> None:
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        conn.commit()


def _run_postgres_pipeline(
    *,
    url: str,
    schema_name: str,
    out_dir: Path,
    dbml_path: Path | None,
    rules_path: Path,
) -> None:
    connector = PostgresConnector.from_config(
        postgres_url=url,
        postgres_schema=schema_name,
        postgres_tables="customers,orders,order_reviews",
        postgres_chunk_rows=2,
    )
    run_pipeline(
        dbml_path=dbml_path,
        csv_dir=None,
        rules_path=rules_path,
        target="order_reviews.review_score",
        out_dir=out_dir,
        source_connector=connector,
    )


def _assert_acceptance_outputs(
    *,
    out_dir: Path,
    url: str,
    schema_name: str,
    expected_parse_status: str,
    expected_issue_types: set[str],
) -> None:
    for artifact in REQUIRED_ARTIFACTS:
        assert (out_dir / artifact).exists(), artifact
    chart_paths = {path.name for path in (out_dir / "charts").glob("*.json")}
    assert REQUIRED_CHARTS.issubset(chart_paths)
    assert not (out_dir / ".connector_extracts").exists()

    metadata = _read_json(out_dir / "connector_metadata.json")
    schema_parse_report = _read_json(out_dir / "schema_parse_report.json")
    schema_evaluation = _read_json(out_dir / "schema_evaluation.json")
    relationship_graph = _read_json(out_dir / "relationship_graph.json")
    lineage_graph = _read_json(out_dir / "lineage_graph.json")
    dataset_verdict = _read_json(out_dir / "dataset_verdict.json")
    table_assessments = _read_json(out_dir / "table_assessments.json")
    run_summary = _read_json(out_dir / "run_summary.json")
    issues = _read_json(out_dir / "issues.json")
    report_md = (out_dir / "report.md").read_text(encoding="utf-8")
    report_html = (out_dir / "report.html").read_text(encoding="utf-8")

    assert metadata["source_type"] == "postgres"
    assert metadata["default_schema"] == schema_name
    assert metadata["chunk_rows"] == 2
    assert metadata["tables_scanned"] == ["customers", "orders", "order_reviews"]
    extracted = {table["table"]: table["rows_extracted"] for table in metadata["tables"]}
    assert extracted == {"customers": 4, "orders": 5, "order_reviews": 5}
    assert metadata["raw_extracts_persisted"] is False
    assert metadata["secrets_redacted"] is True

    assert schema_parse_report["status"] == expected_parse_status
    assert schema_parse_report["counts"]["tables"] == 3
    assert schema_evaluation["summary"]["mapped_table_count"] == 3
    assert relationship_graph["summary"]["edge_count"] == 2
    assert lineage_graph["summary"]["connector_source_type"] == "postgres"
    assert lineage_graph["summary"]["table_count"] == 3
    assert lineage_graph["summary"]["relationship_count"] == 2
    assert "connector_metadata.json" in lineage_graph["evidence_artifacts"]
    assert dataset_verdict["issue_counts"]["total"] == len(issues)
    assert table_assessments["summary"]["table_count"] == 3
    assert run_summary["status"] == "success"
    assert run_summary["inputs"]["postgres_chunk_rows"] == 2
    assert run_summary["artifact_paths"]["connector_metadata"] == "connector_metadata.json"
    assert run_summary["artifact_paths"]["lineage_graph"] == "lineage_graph.json"

    issue_types = {issue["issue_type"] for issue in issues}
    assert expected_issue_types.issubset(issue_types)
    assert "Connector Metadata" in report_html
    assert "Lineage Graph" in report_html
    assert "connector_metadata.json" in report_md
    assert "lineage_graph.json" in report_md
    assert "table_assessments.json" in report_md

    dashboard_payloads = _dashboard_payloads(out_dir)
    dashboard = dashboard_payloads["dashboard"]
    assert dashboard["missing_artifacts"] == []
    assert "connector_metadata.json" in dashboard["artifact_urls"]
    assert "lineage_graph.json" in dashboard["artifact_urls"]
    assert "table_assessments.json" in dashboard["artifact_urls"]
    assert "charts/issue_counts_by_type.json" in dashboard["chart_artifacts"]

    _assert_no_secret_leak(
        out_dir,
        url=url,
        extra_payloads=[dashboard_payloads["job"], dashboard_payloads["dashboard"]],
    )


def _dashboard_payloads(out_dir: Path) -> dict[str, dict]:
    store = WebRunStore(run_root=out_dir.parent / "web_runs")
    job = WebRunJob(
        job_id="postgres_acceptance",
        root_dir=out_dir.parent,
        input_dir=out_dir.parent,
        csv_dir=out_dir.parent,
        out_dir=out_dir,
        input_mode="postgres",
        status="succeeded",
    )
    return {
        "job": store.job_payload(job),
        "dashboard": store.dashboard_payload(job),
    }


def _write_rules(path: Path) -> Path:
    path.write_text(
        """
rules:
  order_reviews:
    - type: range
      column: review_score
      min: 1
      max: 5
      severity: P1
  orders:
    - type: range
      column: order_total
      min: 0
      severity: P2
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_dbml(path: Path) -> Path:
    path.write_text(
        """
Table customers {
  customer_id varchar [pk, not null]
  email varchar [unique]
  customer_state varchar [not null]
}

Table orders {
  order_id varchar [pk, not null]
  customer_id varchar [ref: > customers.customer_id]
  order_total float
  delivered_at timestamp
}

Table order_reviews {
  review_id varchar [pk, not null]
  order_id varchar [ref: > orders.order_id]
  review_score int [not null]
}
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_secret_leak(out_dir: Path, *, url: str, extra_payloads: list[dict]) -> None:
    secrets = _secret_values(url)
    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".log", ".md", ".html"}:
            text = path.read_text(encoding="utf-8")
            for secret in secrets:
                assert secret not in text, f"{secret!r} leaked in {path}"
    for payload in extra_payloads:
        text = json.dumps(payload, sort_keys=True)
        for secret in secrets:
            assert secret not in text, f"{secret!r} leaked in web payload"


def _secret_values(url: str) -> set[str]:
    parsed = urlsplit(url)
    values = {url}
    if "@" in parsed.netloc:
        values.add(parsed.netloc.split("@", 1)[0])
    if parsed.password:
        values.add(parsed.password)
    if parsed.username and parsed.password:
        values.add(f"{parsed.username}:{parsed.password}")
    for key, value in _query_pairs(parsed.query):
        if key.lower() in {"password", "passwd", "pwd", "token", "api_key", "secret"}:
            values.add(value)
    return {value for value in values if value}


def _query_pairs(query: str) -> list[tuple[str, str]]:
    if not query:
        return []
    pairs = []
    for part in query.split("&"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        pairs.append((key, value))
    return pairs

import csv
import json
import os
import uuid
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vsf_profiler.cli import app, run_pipeline
from vsf_profiler.connectors import (
    IntrospectedTable,
    PostgresConnector,
    PostgresTableRef,
    parse_postgres_tables,
    redact_connection_url,
    schema_from_postgres_introspection,
)
from vsf_profiler.models import CatalogTable, CsvCatalog, ColumnSchema, Schema, TableSchema
from vsf_profiler.demo_data import create_small_demo


SECRET_URL = "postgresql://profiler:super-secret@127.0.0.1:5432/demo"
SECRET_QUERY_URL = (
    "postgresql://profiler:super-secret@127.0.0.1:5432/demo"
    "?sslmode=disable&token=query-secret"
)


def test_postgres_table_selection_and_url_redaction():
    refs = parse_postgres_tables(
        "customers, analytics.orders",
        default_schema="public",
    )

    assert [(ref.schema_name, ref.table_name, ref.output_name) for ref in refs] == [
        ("public", "customers", "customers"),
        ("analytics", "orders", "analytics.orders"),
    ]
    assert redact_connection_url(SECRET_URL) == "postgresql://[redacted]@127.0.0.1:5432/demo"
    assert "super-secret" not in redact_connection_url(SECRET_URL)
    redacted_query_url = redact_connection_url(SECRET_QUERY_URL)
    assert redacted_query_url == (
        "postgresql://[redacted]@127.0.0.1:5432/demo?sslmode=disable&token=%5Bredacted%5D"
    )
    assert "super-secret" not in redacted_query_url
    assert "query-secret" not in redacted_query_url


def test_schema_from_postgres_introspection_maps_keys_and_relationships():
    customers = IntrospectedTable(
        ref=PostgresTableRef("public", "customers", "customers"),
        columns=[
            {"name": "customer_id", "type": "varchar", "nullable": False},
            {"name": "email", "type": "varchar", "nullable": True},
        ],
        primary_key=["customer_id"],
        unique_constraints=[["email"]],
    )
    orders = IntrospectedTable(
        ref=PostgresTableRef("public", "orders", "orders"),
        columns=[
            {"name": "order_id", "type": "varchar", "nullable": False},
            {"name": "customer_id", "type": "varchar", "nullable": True},
        ],
        primary_key=["order_id"],
        foreign_keys=[
            {
                "child_columns": ["customer_id"],
                "parent_table": "customers",
                "parent_columns": ["customer_id"],
            }
        ],
    )

    schema = schema_from_postgres_introspection([customers, orders])

    assert schema.tables["customers"].primary_key == ["customer_id"]
    assert schema.tables["customers"].columns["customer_id"].not_null is True
    assert schema.tables["customers"].columns["email"].unique is True
    assert schema.relationships[0].child_table == "orders"
    assert schema.relationships[0].parent_table == "customers"
    fk = schema.tables["orders"].columns["customer_id"].foreign_key
    assert fk is not None
    assert fk.parent_table == "customers"


def test_pipeline_with_connector_writes_metadata_and_redacts_secrets(tmp_path):
    connector = FakeConnector(secret_url=SECRET_URL)
    out_dir = tmp_path / "out"

    run_pipeline(
        dbml_path=None,
        csv_dir=None,
        rules_path=None,
        target=None,
        out_dir=out_dir,
        source_connector=connector,
    )

    assert (out_dir / "profile_summary.json").exists()
    assert (out_dir / "issues.json").exists()
    assert (out_dir / "connector_metadata.json").exists()
    assert (out_dir / "lineage_graph.json").exists()
    assert not (out_dir / ".connector_extracts").exists()

    metadata = json.loads((out_dir / "connector_metadata.json").read_text())
    lineage_graph = json.loads((out_dir / "lineage_graph.json").read_text())
    run_summary = json.loads((out_dir / "run_summary.json").read_text())
    report_md = (out_dir / "report.md").read_text()
    report_html = (out_dir / "report.html").read_text()

    assert metadata["source_type"] == "postgres"
    assert metadata["connection"]["url"] == "postgresql://[redacted]@127.0.0.1:5432/demo"
    assert metadata["tables_scanned"] == ["customers"]
    assert metadata["raw_extracts_persisted"] is False
    assert lineage_graph["summary"]["connector_source_type"] == "postgres"
    assert "connector_metadata.json" in lineage_graph["evidence_artifacts"]
    lineage_nodes = {node["id"]: node for node in lineage_graph["nodes"]}
    lineage_edges = {
        (edge["source"], edge["target"], edge["type"]) for edge in lineage_graph["edges"]
    }
    assert lineage_nodes["source:connector"]["type"] == "source_system"
    assert lineage_nodes["source:connector"]["data"]["connection"]["url"] == (
        "postgresql://[redacted]@127.0.0.1:5432/demo"
    )
    assert ("source:connector", "table:customers", "provides_table") in lineage_edges
    assert "connector_metadata.json" in report_md
    assert "lineage_graph.json" in report_md
    assert "Connector Metadata" in report_html
    assert "Lineage Graph" in report_html
    assert run_summary["inputs"]["source_type"] == "postgres"
    assert run_summary["inputs"]["postgres_url"] == "postgresql://[redacted]@127.0.0.1:5432/demo"
    assert run_summary["artifact_paths"]["lineage_graph"] == "lineage_graph.json"
    assert_no_secret_leak(out_dir, "super-secret")
    assert_no_secret_leak(out_dir, SECRET_URL)


def test_runtime_redacts_secret_strings_on_connector_failure(tmp_path):
    with pytest.raises(RuntimeError, match="boom"):
        run_pipeline(
            dbml_path=None,
            csv_dir=None,
            rules_path=None,
            target=None,
            out_dir=tmp_path / "out",
            source_connector=FailingConnector(secret_url=SECRET_URL),
        )

    assert_no_secret_leak(tmp_path / "out", "super-secret")
    summary = json.loads((tmp_path / "out" / "run_summary.json").read_text())
    assert "[redacted]" in summary["error"]["error_message"]


def test_cli_csv_mode_is_not_hijacked_by_postgres_env(tmp_path, monkeypatch):
    data_dir = create_small_demo(tmp_path / "data")
    out_dir = tmp_path / "csv_out"
    monkeypatch.setenv("VSF_PROFILER_POSTGRES_URL", SECRET_URL)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--dbml",
            str(data_dir / "schema.dbml"),
            "--csv-dir",
            str(data_dir / "csv"),
            "--rules",
            str(data_dir / "rules.yaml"),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "profile_summary.json").exists()
    assert not (out_dir / "connector_metadata.json").exists()


def test_postgres_integration_uses_local_fixture_or_skips(tmp_path):
    url = os.environ.get("VSF_POSTGRES_TEST_URL", "").strip()
    if not url:
        pytest.skip("VSF_POSTGRES_TEST_URL is not configured.")
    psycopg = pytest.importorskip("psycopg")
    schema_name = f"vsf_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
            cur.execute(
                f'''
                CREATE TABLE "{schema_name}"."customers" (
                  customer_id text PRIMARY KEY,
                  email text UNIQUE
                )
                '''
            )
            cur.execute(
                f'''
                CREATE TABLE "{schema_name}"."orders" (
                  order_id text PRIMARY KEY,
                  customer_id text REFERENCES "{schema_name}"."customers"(customer_id),
                  amount numeric
                )
                '''
            )
            cur.execute(
                f'''
                INSERT INTO "{schema_name}"."customers" VALUES
                  ('C001', 'a@example.com'),
                  ('C002', 'b@example.com')
                '''
            )
            cur.execute(
                f'''
                INSERT INTO "{schema_name}"."orders" VALUES
                  ('O001', 'C001', 10.5),
                  ('O002', 'C002', 20.0)
                '''
            )
        conn.commit()

    try:
        out_dir = tmp_path / "pg_out"
        connector = PostgresConnector.from_config(
            postgres_url=url,
            postgres_schema=schema_name,
            postgres_tables="customers,orders",
            postgres_chunk_rows=1,
        )
        run_pipeline(
            dbml_path=None,
            csv_dir=None,
            rules_path=None,
            target=None,
            out_dir=out_dir,
            source_connector=connector,
        )
        metadata = json.loads((out_dir / "connector_metadata.json").read_text())
        relationship_graph = json.loads((out_dir / "relationship_graph.json").read_text())
        assert metadata["source_type"] == "postgres"
        assert metadata["tables_scanned"] == ["customers", "orders"]
        assert relationship_graph["summary"]["edge_count"] == 1
        assert_no_secret_leak(out_dir, url)
    finally:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            conn.commit()


class FakeConnector:
    source_type = "postgres"

    def __init__(self, *, secret_url: str) -> None:
        self.secret_url = secret_url

    def runtime_inputs(self):
        return {
            "source_type": "postgres",
            "postgres_url": self.secret_url,
            "password": "super-secret",
        }

    def prepare_schema(self):
        table = TableSchema(
            name="customers",
            columns={
                "customer_id": ColumnSchema(
                    name="customer_id",
                    type="varchar",
                    is_pk=True,
                    not_null=True,
                ),
                "email": ColumnSchema(name="email", type="varchar", unique=True),
            },
            primary_key=["customer_id"],
        )
        schema = Schema(tables={"customers": table})
        return schema, {
            "artifact": "schema_parse_report",
            "version": 1,
            "parser": "fake_connector",
            "status": "generated_from_connector",
            "source": {"path": ""},
            "counts": {
                "tables": 1,
                "columns": 2,
                "relationships": 0,
                "warnings": 0,
                "errors": 0,
                "unsupported_constructs": 0,
            },
            "diagnostics": [],
            "unsupported_constructs": [],
            "objects": {"tables": [{"name": "customers"}]},
        }

    def build_catalog(self, *, schema, out_dir):
        extract_dir = out_dir / ".connector_extracts" / "fake"
        extract_dir.mkdir(parents=True)
        extract_path = extract_dir / "customers.csv"
        with extract_path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["customer_id", "email"])
            writer.writerow(["C001", "a@example.com"])
            writer.writerow(["C002", "b@example.com"])
        catalog = CsvCatalog(
            tables={
                "customers": CatalogTable(
                    table="customers",
                    csv_path=extract_path,
                    columns=["customer_id", "email"],
                    file_size_mb=0.001,
                    source_type="postgres",
                    source_name="postgres:public.customers",
                )
            }
        )
        metadata = {
            "artifact": "connector_metadata",
            "version": 1,
            "source_type": "postgres",
            "connection": {"url": redact_connection_url(self.secret_url), "provided_by": "test"},
            "introspection_status": "completed",
            "extraction_status": "completed",
            "tables_scanned": ["customers"],
            "tables": [
                {
                    "table": "customers",
                    "source_table": "public.customers",
                    "columns": ["customer_id", "email"],
                    "column_count": 2,
                    "row_count_estimate": 2,
                    "rows_extracted": 2,
                    "status": "extracted",
                }
            ],
            "warnings": [],
            "chunk_rows": 1,
            "raw_extracts_persisted": False,
            "secrets_redacted": True,
        }
        return catalog, metadata, [extract_dir]


class FailingConnector(FakeConnector):
    def prepare_schema(self):
        raise RuntimeError(f"boom {self.secret_url} password=super-secret")


def assert_no_secret_leak(out_dir: Path, secret: str) -> None:
    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".log", ".md", ".html"}:
            assert secret not in path.read_text(encoding="utf-8")

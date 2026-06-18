import csv
import json
from pathlib import Path

from typer.testing import CliRunner

from vsf_profiler.cli import app, run_pipeline
from vsf_profiler.connectors import (
    IntrospectedTable,
    MySQLConnector,
    MySQLTableRef,
    parse_mysql_tables,
    redact_connection_url,
    schema_from_mysql_introspection,
)
from vsf_profiler.demo_data import create_small_demo


SECRET_URL = "mysql://profiler:super-secret@127.0.0.1:3306/demo?token=query-secret"
POSTGRES_SECRET_URL = "postgresql://profiler:pg-secret@127.0.0.1:5432/demo"


def test_mysql_table_selection_and_url_redaction():
    refs = parse_mysql_tables(
        "customers, analytics.orders, `quoted_table`",
        default_schema="demo",
    )

    assert [(ref.schema_name, ref.table_name, ref.output_name) for ref in refs] == [
        ("demo", "customers", "customers"),
        ("analytics", "orders", "analytics.orders"),
        ("demo", "quoted_table", "quoted_table"),
    ]
    redacted_url = redact_connection_url(SECRET_URL)
    assert redacted_url == "mysql://[redacted]@127.0.0.1:3306/demo?token=%5Bredacted%5D"
    assert "super-secret" not in redacted_url
    assert "query-secret" not in redacted_url


def test_schema_from_mysql_introspection_maps_keys_and_relationships():
    customers = IntrospectedTable(
        ref=MySQLTableRef("demo", "customers", "customers"),
        columns=[
            {"name": "customer_id", "type": "varchar", "nullable": False},
            {"name": "email", "type": "varchar", "nullable": True},
        ],
        primary_key=["customer_id"],
        unique_constraints=[["email"]],
    )
    order_items = IntrospectedTable(
        ref=MySQLTableRef("demo", "order_items", "order_items"),
        columns=[
            {"name": "order_id", "type": "varchar", "nullable": False},
            {"name": "line_number", "type": "int", "nullable": False},
            {"name": "customer_id", "type": "varchar", "nullable": True},
        ],
        primary_key=["order_id", "line_number"],
        foreign_keys=[
            {
                "child_columns": ["customer_id"],
                "parent_table": "customers",
                "parent_columns": ["customer_id"],
            }
        ],
    )

    schema = schema_from_mysql_introspection([customers, order_items])

    assert schema.tables["order_items"].primary_key == ["order_id", "line_number"]
    assert schema.tables["order_items"].columns["order_id"].not_null is True
    assert schema.tables["customers"].columns["email"].unique is True
    assert schema.relationships[0].child_table == "order_items"
    assert schema.relationships[0].parent_table == "customers"
    fk = schema.tables["order_items"].columns["customer_id"].foreign_key
    assert fk is not None
    assert fk.parent_table == "customers"


def test_pipeline_with_mysql_connector_writes_metadata_and_redacts_secrets(tmp_path):
    connector = FakeMySQLConnector(secret_url=SECRET_URL)
    out_dir = tmp_path / "mysql_out"

    run_pipeline(
        dbml_path=None,
        csv_dir=None,
        rules_path=None,
        target=None,
        out_dir=out_dir,
        source_connector=connector,
    )

    metadata = json.loads((out_dir / "connector_metadata.json").read_text())
    lineage_graph = json.loads((out_dir / "lineage_graph.json").read_text())
    run_summary = json.loads((out_dir / "run_summary.json").read_text())
    report_md = (out_dir / "report.md").read_text()
    report_html = (out_dir / "report.html").read_text()

    assert metadata["source_type"] == "mysql"
    assert metadata["connection"]["url"] == "mysql://[redacted]@127.0.0.1:3306/demo?token=%5Bredacted%5D"
    assert metadata["default_schema"] == "demo"
    assert metadata["tables_scanned"] == ["customers", "orders"]
    assert metadata["raw_extracts_persisted"] is False
    assert lineage_graph["summary"]["connector_source_type"] == "mysql"
    assert lineage_graph["nodes"][0]["id"]
    assert run_summary["inputs"]["source_type"] == "mysql"
    assert run_summary["inputs"]["mysql_url"].startswith(
        "mysql://[redacted]@127.0.0.1:3306/demo?token="
    )
    assert "[redacted]" in run_summary["inputs"]["mysql_url"]
    assert "Connector Metadata" in report_html
    assert "connector_metadata.json" in report_md
    assert not (out_dir / ".connector_extracts").exists()
    assert_no_secret_leak(out_dir, "super-secret")
    assert_no_secret_leak(out_dir, "query-secret")
    assert_no_secret_leak(out_dir, SECRET_URL)


def test_mysql_connector_supports_dbml_supplied_schema(tmp_path):
    connector = FakeMySQLConnector(secret_url=SECRET_URL)
    dbml_path = tmp_path / "schema.dbml"
    dbml_path.write_text(
        """
        Table customers {
          customer_id varchar [pk]
          email varchar
        }

        Table orders {
          order_id varchar [pk]
          customer_id varchar [ref: > customers.customer_id]
          amount float
        }
        """,
        encoding="utf-8",
    )
    out_dir = tmp_path / "dbml_mysql_out"

    run_pipeline(
        dbml_path=dbml_path,
        csv_dir=None,
        rules_path=None,
        target=None,
        out_dir=out_dir,
        source_connector=connector,
    )

    parse_report = json.loads((out_dir / "schema_parse_report.json").read_text())
    metadata = json.loads((out_dir / "connector_metadata.json").read_text())

    assert parse_report["parser"] == "vsf_profiler.dbml_parser"
    assert metadata["source_type"] == "mysql"
    assert metadata["tables_scanned"] == ["customers", "orders"]


def test_cli_csv_mode_is_not_hijacked_by_mysql_env(tmp_path, monkeypatch):
    data_dir = create_small_demo(tmp_path / "data")
    out_dir = tmp_path / "csv_out"
    monkeypatch.setenv("VSF_PROFILER_MYSQL_URL", SECRET_URL)

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


def test_cli_rejects_both_database_connectors(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--postgres-url",
            POSTGRES_SECRET_URL,
            "--mysql-url",
            SECRET_URL,
            "--out",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Choose only one database connector" in result.output
    assert "super-secret" not in result.output
    assert "pg-secret" not in result.output


class FakeConnection:
    def close(self) -> None:
        return


class FakeMySQLConnector(MySQLConnector):
    def __init__(self, *, secret_url: str) -> None:
        super().__init__(
            connection_url=secret_url,
            selected_tables=parse_mysql_tables("customers,orders", default_schema="demo"),
            default_schema="demo",
            chunk_rows=1,
            provided_by="test",
        )

    def _connect(self):
        return FakeConnection()

    def _introspect_tables(self) -> list[IntrospectedTable]:
        return [
            IntrospectedTable(
                ref=MySQLTableRef("demo", "customers", "customers"),
                columns=[
                    {"name": "customer_id", "type": "varchar", "nullable": False},
                    {"name": "email", "type": "varchar", "nullable": True},
                ],
                primary_key=["customer_id"],
                unique_constraints=[["email"]],
                row_count_estimate=2,
            ),
            IntrospectedTable(
                ref=MySQLTableRef("demo", "orders", "orders"),
                columns=[
                    {"name": "order_id", "type": "varchar", "nullable": False},
                    {"name": "customer_id", "type": "varchar", "nullable": True},
                    {"name": "amount", "type": "float", "nullable": True},
                ],
                primary_key=["order_id"],
                foreign_keys=[
                    {
                        "child_columns": ["customer_id"],
                        "parent_table": "customers",
                        "parent_columns": ["customer_id"],
                    }
                ],
                row_count_estimate=2,
            ),
        ]

    def _export_table(self, conn, table: IntrospectedTable, extract_path: Path) -> int:
        rows = {
            "customers": [
                ["customer_id", "email"],
                ["C001", "a@example.com"],
                ["C002", "b@example.com"],
            ],
            "orders": [
                ["order_id", "customer_id", "amount"],
                ["O001", "C001", "10.5"],
                ["O002", "C002", "20.0"],
            ],
        }[table.ref.output_name]
        with extract_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)
        return len(rows) - 1


def assert_no_secret_leak(out_dir: Path, secret: str) -> None:
    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".log", ".md", ".html"}:
            assert secret not in path.read_text(encoding="utf-8")

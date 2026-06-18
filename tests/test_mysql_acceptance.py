import json
import os
import uuid
from pathlib import Path

import pytest

from vsf_profiler.cli import run_pipeline
from vsf_profiler.connectors import MySQLConnector


def test_mysql_acceptance_uses_local_fixture_or_skips(tmp_path):
    url = os.environ.get("VSF_MYSQL_TEST_URL", "").strip()
    if not url:
        pytest.skip("VSF_MYSQL_TEST_URL is not configured and no mysql tool capability is present.")
    pytest.importorskip("pymysql")

    setup_connector = MySQLConnector.from_config(mysql_url=url)
    customers_table = f"vsf_customers_{uuid.uuid4().hex[:8]}"
    orders_table = f"vsf_orders_{uuid.uuid4().hex[:8]}"
    conn = setup_connector._connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS `{orders_table}`")
            cur.execute(f"DROP TABLE IF EXISTS `{customers_table}`")
            cur.execute(
                f"""
                CREATE TABLE `{customers_table}` (
                  customer_id varchar(32) PRIMARY KEY,
                  email varchar(255) UNIQUE
                ) ENGINE=InnoDB
                """
            )
            cur.execute(
                f"""
                CREATE TABLE `{orders_table}` (
                  order_id varchar(32) PRIMARY KEY,
                  customer_id varchar(32),
                  amount decimal(10, 2),
                  CONSTRAINT `{orders_table}_customer_fk`
                    FOREIGN KEY (customer_id) REFERENCES `{customers_table}`(customer_id)
                ) ENGINE=InnoDB
                """
            )
            cur.execute(
                f"""
                INSERT INTO `{customers_table}` (customer_id, email) VALUES
                  ('C001', 'a@example.com'),
                  ('C002', 'b@example.com')
                """
            )
            cur.execute(
                f"""
                INSERT INTO `{orders_table}` (order_id, customer_id, amount) VALUES
                  ('O001', 'C001', 10.50),
                  ('O002', 'C002', 20.00)
                """
            )
    finally:
        conn.close()

    try:
        out_dir = tmp_path / "mysql_out"
        connector = MySQLConnector.from_config(
            mysql_url=url,
            mysql_tables=f"{customers_table},{orders_table}",
            mysql_chunk_rows=1,
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
        run_summary = json.loads((out_dir / "run_summary.json").read_text())

        assert metadata["source_type"] == "mysql"
        assert metadata["tables_scanned"] == [customers_table, orders_table]
        assert relationship_graph["summary"]["edge_count"] == 1
        assert run_summary["inputs"]["source_type"] == "mysql"
        assert not (out_dir / ".connector_extracts").exists()
        assert_no_secret_leak(out_dir, url)
    finally:
        cleanup_connector = MySQLConnector.from_config(mysql_url=url)
        cleanup_conn = cleanup_connector._connect()
        try:
            with cleanup_conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS `{orders_table}`")
                cur.execute(f"DROP TABLE IF EXISTS `{customers_table}`")
        finally:
            cleanup_conn.close()


def assert_no_secret_leak(out_dir: Path, secret: str) -> None:
    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".log", ".md", ".html"}:
            assert secret not in path.read_text(encoding="utf-8")

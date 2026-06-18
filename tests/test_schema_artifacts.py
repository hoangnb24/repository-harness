import csv
import json

from typer.testing import CliRunner

from vsf_profiler.cli import app, run_pipeline
from vsf_profiler.csv_catalog import build_catalog
from vsf_profiler.dbml_parser import parse_dbml
from vsf_profiler.demo_data import create_small_demo
from vsf_profiler.schema_evaluation import build_schema_evaluation


def test_schema_evaluation_captures_dbml_csv_conformance(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    schema_path.write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
          email varchar [unique]
          region_id varchar [ref: > regions.region_id]
          missing_from_csv varchar
        }

        Table regions {
          region_id varchar [pk, not null]
        }

        Table orders {
          order_id varchar [pk, not null]
        }
        """
    )
    _write_csv(
        csv_dir / "customers.csv",
        ["customer_id", "email", "region_id", "extra_from_csv"],
        [["C001", "c@example.com", "R001", "ignored"]],
    )
    _write_csv(csv_dir / "regions.csv", ["region_id"], [["R001"]])
    _write_csv(csv_dir / "loose_extract.csv", ["loose_id"], [["L001"]])

    schema = parse_dbml(schema_path)
    catalog = build_catalog(csv_dir, schema)
    evaluation = build_schema_evaluation(schema=schema, catalog=catalog, issues=[])

    assert evaluation["summary"]["dbml_table_count"] == 3
    assert evaluation["schema_meta"] == {"total_tables": 3, "total_relationships": 1}
    assert evaluation["summary"]["mapped_table_count"] == 2
    assert evaluation["missing_tables"] == ["orders"]
    assert evaluation["extra_csvs"] == [
        {"table": "loose_extract", "csv_path": "loose_extract.csv", "status": "extra_csv"}
    ]
    customers = next(table for table in evaluation["tables"] if table["table"] == "customers")
    assert customers["status"] == "mapped"
    assert customers["primary_key"] == ["customer_id"]
    assert customers["foreign_keys"] == [
        {"column": "region_id", "parent_table": "regions", "parent_column": "region_id"}
    ]
    assert evaluation["relationships"] == [
        {
            "id": "customers.region_id->regions.region_id",
            "child_table": "customers",
            "child_column": "region_id",
            "child_columns": ["region_id"],
            "parent_table": "regions",
            "parent_column": "region_id",
            "parent_columns": ["region_id"],
            "relationship_type": "explicit_fk",
            "dbml_operator": ">",
            "declared_cardinality": "MANY_TO_ONE",
            "status": "declared_in_schema",
            "confidence": 1.0,
        }
    ]
    assert evaluation["summary"]["relationship_cardinality_counts"] == {"MANY_TO_ONE": 1}
    assert evaluation["summary"]["composite_relationship_count"] == 0
    assert evaluation["summary"]["junction_table_count"] == 0
    assert customers["missing_columns"] == ["missing_from_csv"]
    assert customers["extra_columns"] == ["extra_from_csv"]
    missing_column = next(column for column in customers["columns"] if column["name"] == "missing_from_csv")
    assert missing_column["in_dbml"] is True
    assert missing_column["in_csv"] is False
    extra_column = next(column for column in customers["columns"] if column["name"] == "extra_from_csv")
    assert extra_column["in_dbml"] is False
    assert extra_column["in_csv"] is True


def test_csv_catalog_preserves_exact_mapping_and_infers_strong_header_match(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    schema_path.write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
          email varchar
          region_id varchar [ref: > regions.region_id]
        }

        Table regions {
          region_id varchar [pk, not null]
        }
        """,
        encoding="utf-8",
    )
    _write_csv(
        csv_dir / "crm_customer_export.csv",
        ["customer_id", "email", "region_id"],
        [["C001", "c@example.com", "R001"]],
    )
    _write_csv(csv_dir / "regions.csv", ["region_id"], [["R001"]])

    schema = parse_dbml(schema_path)
    catalog = build_catalog(csv_dir, schema)
    evaluation = build_schema_evaluation(schema=schema, catalog=catalog, issues=[])

    assert catalog.tables["regions"].mapping_method == "exact"
    assert catalog.tables["customers"].csv_path.name == "crm_customer_export.csv"
    assert catalog.tables["customers"].mapping_method == "inferred"
    assert catalog.extra_csvs == []

    customers = next(table for table in evaluation["tables"] if table["table"] == "customers")
    assert customers["status"] == "mapped"
    assert customers["mapping_method"] == "inferred"
    assert customers["selected_csv"] == "crm_customer_export.csv"
    assert customers["confidence"] >= 0.8
    assert customers["matched_columns"] == ["customer_id", "email", "region_id"]
    assert customers["missing_columns"] == []
    assert customers["extra_columns"] == []
    assert customers["candidates"][0]["csv_path"] == "crm_customer_export.csv"
    assert evaluation["summary"]["mapping_method_counts"] == {"exact": 1, "inferred": 1}


def test_csv_catalog_leaves_ambiguous_header_matches_unmapped_with_evidence(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    schema_path.write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
          email varchar
          region_id varchar
        }
        """,
        encoding="utf-8",
    )
    header = ["customer_id", "email", "region_id"]
    _write_csv(csv_dir / "customer_extract_a.csv", header, [["C001", "a@example.com", "R001"]])
    _write_csv(csv_dir / "customer_extract_b.csv", header, [["C002", "b@example.com", "R002"]])

    schema = parse_dbml(schema_path)
    catalog = build_catalog(csv_dir, schema)
    evaluation = build_schema_evaluation(schema=schema, catalog=catalog, issues=[])

    assert "customers" not in catalog.tables
    assert catalog.missing_tables == ["customers"]
    evidence = catalog.mapping_evidence["customers"]
    assert evidence.mapping_method == "ambiguous"
    assert evidence.status == "ambiguous"
    assert len(evidence.candidates) == 2

    customers = evaluation["tables"][0]
    assert customers["status"] == "ambiguous"
    assert customers["mapping_method"] == "ambiguous"
    assert customers["selected_csv"] is None
    assert "too close" in customers["ambiguity_reason"]
    assert [candidate["csv_path"] for candidate in customers["candidates"]] == [
        "customer_extract_b.csv",
        "customer_extract_a.csv",
    ]


def test_pipeline_manual_mapping_override_writes_mapping_evidence_and_reports(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    schema_path.write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
          email varchar
        }
        """,
        encoding="utf-8",
    )
    _write_csv(csv_dir / "crm_export.csv", ["customer_id", "email"], [["C001", "a@example.com"]])
    mapping_path = root / "mapping.yaml"
    mapping_path.write_text("mappings:\n  customers: crm_export.csv\n", encoding="utf-8")
    out_dir = root / "out"

    run_pipeline(
        dbml_path=schema_path,
        csv_dir=csv_dir,
        mapping_path=mapping_path,
        rules_path=None,
        target=None,
        out_dir=out_dir,
    )

    schema_evaluation = json.loads((out_dir / "schema_evaluation.json").read_text())
    schema_diagram = json.loads((out_dir / "schema_diagram.json").read_text())
    report_md = (out_dir / "report.md").read_text()
    report_html = (out_dir / "report.html").read_text()

    customers = schema_evaluation["tables"][0]
    assert customers["mapping_method"] == "manual"
    assert customers["selected_csv"] == "crm_export.csv"
    assert customers["matched_columns"] == ["customer_id", "email"]
    assert schema_evaluation["summary"]["mapping_method_counts"] == {"manual": 1}
    assert schema_diagram["tables"][0]["status"] == "manual"
    assert "manual" in report_md
    assert "manual" in report_html


def test_cli_run_accepts_mapping_override_file(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    schema_path.write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
          email varchar
        }
        """,
        encoding="utf-8",
    )
    _write_csv(csv_dir / "crm_export.csv", ["customer_id", "email"], [["C001", "a@example.com"]])
    mapping_path = root / "mapping.json"
    mapping_path.write_text(json.dumps({"customers": "crm_export.csv"}), encoding="utf-8")
    out_dir = root / "out"

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--dbml",
            str(schema_path),
            "--csv-dir",
            str(csv_dir),
            "--mapping",
            str(mapping_path),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    schema_evaluation = json.loads((out_dir / "schema_evaluation.json").read_text())
    assert schema_evaluation["tables"][0]["mapping_method"] == "manual"


def test_pipeline_writes_relationship_graph_metrics_and_evidence(tmp_path):
    data_dir = create_small_demo(tmp_path / "demo")
    out_dir = tmp_path / "out"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
    )

    schema_evaluation = json.loads((out_dir / "schema_evaluation.json").read_text())
    schema_parse_report = json.loads((out_dir / "schema_parse_report.json").read_text())
    relationship_graph = json.loads((out_dir / "relationship_graph.json").read_text())
    report_md = (out_dir / "report.md").read_text()
    report_html = (out_dir / "report.html").read_text()

    assert schema_parse_report["artifact"] == "schema_parse_report"
    assert schema_parse_report["counts"]["tables"] == 7
    assert schema_parse_report["counts"]["relationships"] == 6
    assert schema_parse_report["status"] == "parsed"
    assert schema_evaluation["summary"]["mapped_table_count"] == 7
    assert schema_evaluation["summary"]["missing_table_count"] == 0
    assert schema_evaluation["summary"]["schema_issue_count"] > 0
    assert relationship_graph["summary"]["node_count"] == 7
    assert relationship_graph["summary"]["edge_count"] == 6
    assert relationship_graph["summary"]["status_counts"]["invalid"] >= 1

    orders_customers = next(
        edge
        for edge in relationship_graph["edges"]
        if edge["source_table"] == "orders" and edge["target_table"] == "customers"
    )
    assert orders_customers["status"] == "invalid"
    assert orders_customers["relationship_type"] == "explicit_fk"
    assert orders_customers["confidence"] == 1.0
    assert orders_customers["cardinality"] == "MANY_TO_ONE"
    assert orders_customers["declared_cardinality"] == "MANY_TO_ONE"
    assert orders_customers["source_columns"] == ["customer_id"]
    assert orders_customers["target_columns"] == ["customer_id"]
    assert orders_customers["role"] == "child_to_parent"
    assert orders_customers["metrics"]["orphan_count"] == 1
    assert orders_customers["metrics"]["join_coverage"] == 0.75
    assert any(link["issue_type"] == "ORPHAN_FOREIGN_KEY" for link in orders_customers["evidence_links"])
    assert "schema_evaluation.json" in report_md
    assert "schema_parse_report.json" in report_md
    assert "relationship_graph.json" in report_md
    assert "schema_evaluation.json" in report_html
    assert "schema_parse_report.json" in report_html
    assert "relationship_graph.json" in report_html


def _write_csv(path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)

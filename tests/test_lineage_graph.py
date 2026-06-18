import json

from vsf_profiler.cli import run_pipeline
from vsf_profiler.demo_data import create_small_demo


def test_demo_lineage_graph_links_sources_schema_stages_and_artifacts(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
    )

    lineage = json.loads((out_dir / "lineage_graph.json").read_text())
    nodes = {node["id"]: node for node in lineage["nodes"]}
    edges = {(edge["source"], edge["target"], edge["type"]) for edge in lineage["edges"]}

    assert lineage["artifact"] == "lineage_graph"
    assert lineage["version"] == 1
    assert lineage["summary"]["source_system_count"] == 2
    assert lineage["summary"]["table_count"] == 7
    assert lineage["summary"]["column_count"] >= 27
    assert lineage["summary"]["relationship_count"] == 6
    assert lineage["summary"]["stage_count"] == 8
    assert lineage["summary"]["artifact_count"] >= 20
    assert lineage["summary"]["edge_count"] == len(lineage["edges"])
    assert {
        "schema_parse_report.json",
        "schema_evaluation.json",
        "relationship_graph.json",
        "run_events.jsonl",
        "run_summary.json",
    }.issubset(set(lineage["evidence_artifacts"]))

    assert nodes["source:csv"]["type"] == "source_system"
    assert nodes["source:dbml"]["type"] == "source_system"
    assert nodes["schema:dbml"]["type"] == "schema"
    assert nodes["table:orders"]["type"] == "table"
    assert nodes["column:orders.customer_id"]["type"] == "column"
    assert nodes["relationship:orders.customer_id->customers.customer_id"]["type"] == "relationship"
    assert nodes["stage:write_machine_artifacts"]["type"] == "profiler_stage"
    assert nodes["artifact:profile_summary.json"]["type"] == "artifact"

    assert ("source:dbml", "schema:dbml", "provides_schema") in edges
    assert ("source:csv", "table:orders", "provides_table") in edges
    assert ("schema:dbml", "table:orders", "defines_table") in edges
    assert ("table:orders", "column:orders.customer_id", "has_column") in edges
    assert (
        "relationship:orders.customer_id->customers.customer_id",
        "artifact:relationship_graph.json",
        "summarized_by",
    ) in edges
    assert (
        "stage:write_machine_artifacts",
        "artifact:profile_summary.json",
        "produces_artifact",
    ) in edges
    assert (
        "artifact:issues.json",
        "artifact:dataset_verdict.json",
        "supports_artifact",
    ) in edges
    assert (
        "artifact:lineage_graph.json",
        "artifact:report.md",
        "supports_artifact",
    ) in edges

    lineage_text = json.dumps(lineage)
    assert "review_score\n" not in lineage_text

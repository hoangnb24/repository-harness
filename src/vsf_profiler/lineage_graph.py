from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from vsf_profiler.connectors import redact_secret_text
from vsf_profiler.models import CsvCatalog, Schema
from vsf_profiler.relationship_metadata import child_columns, parent_columns, relationship_id


SENSITIVE_KEY_PARTS = ("secret", "token", "credential", "password", "api_key")
BASE_EVIDENCE_ARTIFACTS = [
    "profile_summary.json",
    "issues.json",
    "schema_parse_report.json",
    "schema_evaluation.json",
    "relationship_graph.json",
    "dataset_verdict.json",
    "table_assessments.json",
    "run_events.jsonl",
    "run_summary.json",
]
MACHINE_REPORT_SOURCES = [
    "profile_summary.json",
    "issues.json",
    "influence.json",
    "schema_parse_report.json",
    "schema_evaluation.json",
    "relationship_graph.json",
    "dataset_verdict.json",
    "table_assessments.json",
    "lineage_graph.json",
]


def build_lineage_graph(
    *,
    schema: Schema,
    catalog: CsvCatalog,
    profile_summary: dict[str, Any],
    issues: list[dict[str, Any]],
    schema_parse_report: dict[str, Any],
    schema_evaluation: dict[str, Any],
    relationship_graph: dict[str, Any],
    dataset_verdict: dict[str, Any],
    table_assessments: dict[str, Any],
    chart_specs: dict[str, dict[str, Any]],
    run_summary: dict[str, Any],
    run_events: list[dict[str, Any]],
    connector_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    edge_ids: set[tuple[str, str, str]] = set()
    warnings: list[str] = []

    def add_node(
        node_id: str,
        node_type: str,
        label: str,
        *,
        data: dict[str, Any] | None = None,
        evidence: list[str] | None = None,
    ) -> None:
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "label": label,
                "data": _safe(data or {}),
                "evidence": sorted(set(evidence or [])),
            }
        )

    def add_edge(
        source: str,
        target: str,
        edge_type: str,
        *,
        evidence: list[str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        if source not in node_ids or target not in node_ids:
            warnings.append(f"Skipped edge with missing node: {source} -[{edge_type}]-> {target}")
            return
        key = (source, target, edge_type)
        if key in edge_ids:
            return
        edge_ids.add(key)
        edges.append(
            {
                "source": source,
                "target": target,
                "type": edge_type,
                "evidence": sorted(set(evidence or [])),
                "data": _safe(data or {}),
            }
        )

    source_ids = _add_source_nodes(
        add_node,
        connector_metadata=connector_metadata,
        run_summary=run_summary,
    )
    schema_id = _schema_node_id(schema_parse_report)
    add_node(
        schema_id,
        "schema",
        "Connector-introspected schema"
        if schema_parse_report.get("status") == "generated_from_connector"
        else "DBML schema",
        data={
            "parser": schema_parse_report.get("parser", ""),
            "status": schema_parse_report.get("status", ""),
            "counts": schema_parse_report.get("counts") or {},
        },
        evidence=["schema_parse_report.json"],
    )
    if "source:dbml" in source_ids:
        add_edge("source:dbml", schema_id, "provides_schema", evidence=["schema_parse_report.json"])
    if connector_metadata and "source:connector" in source_ids:
        add_edge(
            "source:connector",
            schema_id,
            "provides_schema",
            evidence=["connector_metadata.json", "schema_parse_report.json"],
        )

    profile_tables = profile_summary.get("tables") or {}
    schema_eval_tables = {
        str(table.get("table", "")): table
        for table in schema_evaluation.get("tables", [])
        if table.get("table")
    }
    table_node_ids: dict[str, str] = {}
    column_node_ids: dict[tuple[str, str], str] = {}
    for table_name, table_schema in schema.tables.items():
        table_id = _table_id(table_name)
        table_node_ids[table_name] = table_id
        table_profile = profile_tables.get(table_name) or {}
        catalog_table = catalog.tables.get(table_name)
        source_type = catalog_table.source_type if catalog_table else ""
        add_node(
            table_id,
            "table",
            table_name,
            data={
                "table": table_name,
                "status": "mapped" if catalog_table else "missing_source",
                "source_type": source_type,
                "source_name": catalog_table.source_name if catalog_table else "",
                "row_count": table_profile.get("row_count"),
                "column_count": table_profile.get("column_count", len(table_schema.columns)),
                "primary_key": list(table_schema.primary_key),
                "unique_constraints": list(table_schema.unique_constraints),
            },
            evidence=["schema_evaluation.json", "profile_summary.json"],
        )
        add_edge(
            schema_id,
            table_id,
            "defines_table",
            evidence=["schema_parse_report.json", "schema_evaluation.json"],
        )
        source_id = "source:connector" if connector_metadata else "source:csv"
        if catalog_table and source_id in source_ids:
            add_edge(
                source_id,
                table_id,
                "provides_table",
                evidence=[
                    "connector_metadata.json" if connector_metadata else "profile_summary.json",
                    "schema_evaluation.json",
                ],
                data={"source_name": catalog_table.source_name or str(catalog_table.csv_path)},
            )
        table_eval = schema_eval_tables.get(table_name) or {}
        eval_columns = {
            str(column.get("name", "")): column
            for column in table_eval.get("columns", [])
            if column.get("name")
        }
        column_names = list(dict.fromkeys([*table_schema.columns, *eval_columns]))
        for column_name in column_names:
            column_schema = table_schema.columns.get(column_name)
            column_eval = eval_columns.get(column_name) or {}
            column_id = _column_id(table_name, column_name)
            column_node_ids[(table_name, column_name)] = column_id
            add_node(
                column_id,
                "column",
                f"{table_name}.{column_name}",
                data={
                    "table": table_name,
                    "column": column_name,
                    "in_schema": column_schema is not None,
                    "in_source": column_eval.get("in_csv"),
                    "dbml_type": column_schema.type if column_schema else column_eval.get("dbml_type"),
                    "is_pk": column_schema.is_pk if column_schema else column_eval.get("is_pk", False),
                    "not_null": column_schema.not_null
                    if column_schema
                    else column_eval.get("not_null", False),
                    "unique": column_schema.unique
                    if column_schema
                    else column_eval.get("unique", False),
                },
                evidence=["schema_parse_report.json", "schema_evaluation.json"],
            )
            add_edge(
                table_id,
                column_id,
                "has_column",
                evidence=["schema_parse_report.json", "schema_evaluation.json"],
            )

    relationship_node_ids = _add_relationship_nodes(
        add_node,
        add_edge,
        schema=schema,
        relationship_graph=relationship_graph,
        schema_id=schema_id,
        table_node_ids=table_node_ids,
        column_node_ids=column_node_ids,
    )
    artifact_node_ids = _add_artifact_nodes(add_node, run_summary=run_summary)
    stage_node_ids = _add_stage_nodes(add_node, run_summary=run_summary)
    _add_stage_artifact_edges(
        add_edge,
        stage_node_ids=stage_node_ids,
        artifact_node_ids=artifact_node_ids,
    )
    _add_artifact_dependency_edges(
        add_edge,
        artifact_node_ids=artifact_node_ids,
        chart_specs=chart_specs,
    )
    _add_table_artifact_edges(
        add_edge,
        artifact_node_ids=artifact_node_ids,
        table_node_ids=table_node_ids,
        column_node_ids=column_node_ids,
        relationship_node_ids=relationship_node_ids,
        issues=issues,
    )

    event_count = len(run_events)
    if "artifact:run_events.jsonl" in artifact_node_ids.values():
        for stage_id in stage_node_ids.values():
            add_edge(
                stage_id,
                "artifact:run_events.jsonl",
                "recorded_in",
                evidence=["run_events.jsonl"],
                data={"event_count": event_count},
            )

    type_counts = Counter(node["type"] for node in nodes)
    table_assessment_count = len(table_assessments.get("assessments") or [])
    evidence_artifacts = list(BASE_EVIDENCE_ARTIFACTS)
    if connector_metadata:
        evidence_artifacts.insert(3, "connector_metadata.json")

    return _safe(
        {
            "artifact": "lineage_graph",
            "version": 1,
            "summary": {
                "source_system_count": type_counts.get("source_system", 0),
                "schema_count": type_counts.get("schema", 0),
                "table_count": type_counts.get("table", 0),
                "column_count": type_counts.get("column", 0),
                "relationship_count": type_counts.get("relationship", 0),
                "stage_count": type_counts.get("profiler_stage", 0),
                "artifact_count": type_counts.get("artifact", 0),
                "edge_count": len(edges),
                "connector_source_type": (connector_metadata or {}).get("source_type", ""),
                "table_assessment_count": table_assessment_count,
            },
            "evidence_artifacts": evidence_artifacts,
            "nodes": sorted(nodes, key=lambda node: (node["type"], node["id"])),
            "edges": sorted(edges, key=lambda edge: (edge["source"], edge["type"], edge["target"])),
            "warnings": sorted(set(warnings)),
        }
    )


def read_run_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _add_source_nodes(
    add_node,
    *,
    connector_metadata: dict[str, Any] | None,
    run_summary: dict[str, Any],
) -> set[str]:
    inputs = run_summary.get("inputs") or {}
    source_ids: set[str] = set()
    if connector_metadata:
        source_ids.add("source:connector")
        source_type = str(connector_metadata.get("source_type") or "connector")
        add_node(
            "source:connector",
            "source_system",
            f"{source_type} source",
            data={
                "source_type": source_type,
                "connection": connector_metadata.get("connection") or {},
                "default_schema": connector_metadata.get("default_schema", ""),
                "introspection_status": connector_metadata.get("introspection_status", ""),
                "extraction_status": connector_metadata.get("extraction_status", ""),
                "tables_scanned": connector_metadata.get("tables_scanned") or [],
                "raw_extracts_persisted": connector_metadata.get("raw_extracts_persisted", False),
                "secrets_redacted": connector_metadata.get("secrets_redacted", False),
            },
            evidence=["connector_metadata.json", "run_summary.json"],
        )
        return source_ids

    source_ids.add("source:csv")
    add_node(
        "source:csv",
        "source_system",
        "CSV directory",
        data={"source_type": "csv", "path": inputs.get("csv_dir", "")},
        evidence=["profile_summary.json", "run_summary.json"],
    )
    if inputs.get("dbml_path"):
        source_ids.add("source:dbml")
        add_node(
            "source:dbml",
            "source_system",
            "DBML file",
            data={"source_type": "dbml", "path": inputs.get("dbml_path", "")},
            evidence=["schema_parse_report.json", "run_summary.json"],
        )
    return source_ids


def _add_relationship_nodes(
    add_node,
    add_edge,
    *,
    schema: Schema,
    relationship_graph: dict[str, Any],
    schema_id: str,
    table_node_ids: dict[str, str],
    column_node_ids: dict[tuple[str, str], str],
) -> dict[str, str]:
    by_id = {
        str(edge.get("id", "")): edge
        for edge in relationship_graph.get("edges", [])
        if edge.get("id")
    }
    relationship_node_ids: dict[str, str] = {}
    for rel in schema.relationships:
        rel_id = relationship_id(rel)
        edge_payload = by_id.get(rel_id) or {}
        node_id = _relationship_node_id(rel_id)
        relationship_node_ids[rel_id] = node_id
        add_node(
            node_id,
            "relationship",
            rel_id,
            data={
                "relationship_id": rel_id,
                "child_table": rel.child_table,
                "child_columns": child_columns(rel),
                "parent_table": rel.parent_table,
                "parent_columns": parent_columns(rel),
                "declared_cardinality": rel.declared_cardinality,
                "observed_cardinality": edge_payload.get("observed_cardinality", ""),
                "status": edge_payload.get("status", ""),
                "metrics": edge_payload.get("metrics") or {},
            },
            evidence=["schema_evaluation.json", "relationship_graph.json"],
        )
        add_edge(
            schema_id,
            node_id,
            "defines_relationship",
            evidence=["schema_parse_report.json", "schema_evaluation.json"],
        )
        for table_name, edge_type in [
            (rel.child_table, "uses_child_table"),
            (rel.parent_table, "uses_parent_table"),
        ]:
            table_id = table_node_ids.get(table_name)
            if table_id:
                add_edge(
                    node_id,
                    table_id,
                    edge_type,
                    evidence=["schema_evaluation.json", "relationship_graph.json"],
                )
        for column_name in child_columns(rel):
            column_id = column_node_ids.get((rel.child_table, column_name))
            if column_id:
                add_edge(
                    node_id,
                    column_id,
                    "uses_child_column",
                    evidence=["schema_evaluation.json", "relationship_graph.json"],
                )
        for column_name in parent_columns(rel):
            column_id = column_node_ids.get((rel.parent_table, column_name))
            if column_id:
                add_edge(
                    node_id,
                    column_id,
                    "uses_parent_column",
                    evidence=["schema_evaluation.json", "relationship_graph.json"],
                )
    return relationship_node_ids


def _add_artifact_nodes(add_node, *, run_summary: dict[str, Any]) -> dict[str, str]:
    artifact_node_ids: dict[str, str] = {}
    artifact_paths = run_summary.get("artifact_paths") or {}
    for key, path in sorted(artifact_paths.items()):
        if not isinstance(path, str):
            continue
        artifact_id = _artifact_id(path)
        artifact_node_ids[path] = artifact_id
        add_node(
            artifact_id,
            "artifact",
            path,
            data={"artifact_key": key, "path": path, "kind": _artifact_kind(path)},
            evidence=["run_summary.json"],
        )
    return artifact_node_ids


def _add_stage_nodes(add_node, *, run_summary: dict[str, Any]) -> dict[str, str]:
    stage_node_ids: dict[str, str] = {}
    for stage in run_summary.get("stage_timings", []):
        name = str(stage.get("name", ""))
        if not name:
            continue
        stage_id = f"stage:{name}"
        stage_node_ids[name] = stage_id
        add_node(
            stage_id,
            "profiler_stage",
            stage.get("display_name") or name,
            data={
                "name": name,
                "status": stage.get("status", ""),
                "duration_seconds": stage.get("duration_seconds"),
                "details": stage.get("details") or {},
            },
            evidence=["run_summary.json", "run_events.jsonl"],
        )
    return stage_node_ids


def _add_stage_artifact_edges(
    add_edge,
    *,
    stage_node_ids: dict[str, str],
    artifact_node_ids: dict[str, str],
) -> None:
    stage_outputs = {
        "parse_dbml_schema": ["schema_parse_report.json"],
        "catalog_csv_files": ["connector_metadata.json"],
        "profile_csv_tables": ["profile_summary.json"],
        "data_quality_checks": ["issues.json"],
        "relationship_checks": ["relationship_graph.json"],
        "influence_analysis": ["influence.json"],
        "write_machine_artifacts": [
            "profile_summary.json",
            "issues.json",
            "influence.json",
            "schema_parse_report.json",
            "connector_metadata.json",
            "schema_evaluation.json",
            "relationship_graph.json",
            "dataset_verdict.json",
            "table_assessments.json",
            "schema_diagram.json",
            "schema_diagram.dbml",
        ],
        "llm_narrative": ["l4_report.md", "guardrail_report.json"],
        "render_reports": ["report.md", "report.html", "lineage_graph.json"],
    }
    for stage_name, artifact_paths in stage_outputs.items():
        stage_id = stage_node_ids.get(stage_name)
        if not stage_id:
            continue
        for path in artifact_paths:
            artifact_id = artifact_node_ids.get(path)
            if artifact_id:
                add_edge(
                    stage_id,
                    artifact_id,
                    "produces_artifact",
                    evidence=["run_summary.json", "run_events.jsonl"],
                )
    write_stage = stage_node_ids.get("write_machine_artifacts")
    if write_stage:
        for path, artifact_id in artifact_node_ids.items():
            if path.startswith("charts/"):
                add_edge(
                    write_stage,
                    artifact_id,
                    "produces_artifact",
                    evidence=["run_summary.json", "run_events.jsonl"],
                )


def _add_artifact_dependency_edges(
    add_edge,
    *,
    artifact_node_ids: dict[str, str],
    chart_specs: dict[str, dict[str, Any]],
) -> None:
    dependencies = {
        "schema_evaluation.json": ["schema_parse_report.json", "issues.json"],
        "relationship_graph.json": ["schema_parse_report.json", "issues.json"],
        "dataset_verdict.json": ["issues.json", "schema_evaluation.json", "relationship_graph.json"],
        "table_assessments.json": [
            "profile_summary.json",
            "issues.json",
            "relationship_graph.json",
            "dataset_verdict.json",
        ],
        "influence.json": ["profile_summary.json"],
        "lineage_graph.json": [
            "schema_parse_report.json",
            "schema_evaluation.json",
            "relationship_graph.json",
            "table_assessments.json",
            "run_events.jsonl",
            "run_summary.json",
        ],
        "report.md": MACHINE_REPORT_SOURCES,
        "report.html": MACHINE_REPORT_SOURCES,
    }
    for target_path, source_paths in dependencies.items():
        target_id = artifact_node_ids.get(target_path)
        if not target_id:
            continue
        for source_path in source_paths:
            source_id = artifact_node_ids.get(source_path)
            if source_id:
                add_edge(
                    source_id,
                    target_id,
                    "supports_artifact",
                    evidence=[target_path, source_path],
                )

    for filename, spec in chart_specs.items():
        chart_path = f"charts/{filename}"
        target_id = artifact_node_ids.get(chart_path)
        if not target_id:
            continue
        for source_path in spec.get("source_artifacts", []):
            source_id = artifact_node_ids.get(source_path)
            if source_id:
                add_edge(
                    source_id,
                    target_id,
                    "supports_chart",
                    evidence=[chart_path, source_path],
                )


def _add_table_artifact_edges(
    add_edge,
    *,
    artifact_node_ids: dict[str, str],
    table_node_ids: dict[str, str],
    column_node_ids: dict[tuple[str, str], str],
    relationship_node_ids: dict[str, str],
    issues: list[dict[str, Any]],
) -> None:
    profile_artifact = artifact_node_ids.get("profile_summary.json")
    if profile_artifact:
        for table_id in table_node_ids.values():
            add_edge(
                table_id,
                profile_artifact,
                "summarized_by",
                evidence=["profile_summary.json"],
            )

    issues_artifact = artifact_node_ids.get("issues.json")
    if issues_artifact:
        for issue in issues:
            table_id = table_node_ids.get(str(issue.get("table", "")))
            if table_id:
                add_edge(
                    table_id,
                    issues_artifact,
                    "has_issue_evidence",
                    evidence=["issues.json"],
                    data={
                        "issue_id": issue.get("issue_id", ""),
                        "issue_type": issue.get("issue_type", ""),
                        "severity": issue.get("severity", ""),
                    },
                )
            for column in issue.get("columns") or []:
                column_id = column_node_ids.get((str(issue.get("table", "")), str(column)))
                if column_id:
                    add_edge(
                        column_id,
                        issues_artifact,
                        "has_issue_evidence",
                        evidence=["issues.json"],
                        data={"issue_id": issue.get("issue_id", "")},
                    )

    relationship_artifact = artifact_node_ids.get("relationship_graph.json")
    if relationship_artifact:
        for relationship_id_value, node_id in relationship_node_ids.items():
            add_edge(
                node_id,
                relationship_artifact,
                "summarized_by",
                evidence=["relationship_graph.json"],
                data={"relationship_id": relationship_id_value},
            )


def _schema_node_id(schema_parse_report: dict[str, Any]) -> str:
    if schema_parse_report.get("status") == "generated_from_connector":
        return "schema:connector"
    return "schema:dbml"


def _table_id(table: str) -> str:
    return f"table:{table}"


def _column_id(table: str, column: str) -> str:
    return f"column:{table}.{column}"


def _relationship_node_id(rel_id: str) -> str:
    return f"relationship:{rel_id}"


def _artifact_id(path: str) -> str:
    return f"artifact:{path}"


def _artifact_kind(path: str) -> str:
    if path.startswith("charts/"):
        return "chart_spec"
    if path.startswith("samples/"):
        return "sample"
    if path.endswith(".json"):
        return "json"
    if path.endswith(".jsonl"):
        return "jsonl"
    if path.endswith(".md"):
        return "markdown"
    if path.endswith(".html"):
        return "html"
    if path.endswith(".log"):
        return "log"
    return "artifact"


def _safe(value: Any, *, key: str | None = None) -> Any:
    if (
        key
        and key.lower() not in {"secret_redacted", "secrets_redacted"}
        and any(part in key.lower() for part in SENSITIVE_KEY_PARTS)
    ):
        return "[redacted]"
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        return redact_secret_text(value)
    if isinstance(value, dict):
        return {
            str(item_key): _safe(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [_safe(item) for item in value]
    return redact_secret_text(str(value))

from __future__ import annotations

from collections import Counter
from typing import Any

from vsf_profiler.csv_catalog import CsvCatalog
from vsf_profiler.models import Issue, ProfileSummary, Relationship, Schema
from vsf_profiler.relationship_metadata import (
    child_columns,
    detect_junction_tables,
    endpoint_label,
    many_to_many_relationships,
    parent_columns,
    relationship_id,
)


RELATIONSHIP_ISSUE_TYPES = {
    "FOREIGN_KEY_NULL",
    "ORPHAN_FOREIGN_KEY",
    "PARENT_KEY_DUPLICATE",
    "CHILD_RELATIONSHIP_DUPLICATE",
}


def build_relationship_graph(
    *,
    schema: Schema,
    catalog: CsvCatalog,
    profile: ProfileSummary,
    relationship_summaries: list[dict[str, Any]],
    issues: list[Issue],
) -> dict[str, Any]:
    edges = [
        _relationship_edge(rel, catalog, relationship_summaries, issues)
        for rel in schema.relationships
    ]
    status_counts = Counter(edge["status"] for edge in edges)
    cardinality_counts = Counter(edge["cardinality"] for edge in edges)
    non_unique_parent_tables = sorted(
        {
            edge["target_table"]
            for edge in edges
            if (edge["metrics"].get("parent_duplicate_count") or 0) > 0
        }
    )
    junction_tables = detect_junction_tables(schema)
    many_to_many = many_to_many_relationships(schema)
    return {
        "artifact": "relationship_graph",
        "version": 1,
        "summary": {
            "node_count": len(schema.tables),
            "edge_count": len(edges),
            "status_counts": dict(sorted(status_counts.items())),
            "cardinality_counts": dict(sorted(cardinality_counts.items())),
            "junction_table_count": len(junction_tables),
            "many_to_many_relationship_count": len(many_to_many),
        },
        "nodes": [_table_node(table_name, schema, catalog, profile) for table_name in schema.tables],
        "edges": edges,
        "junction_tables": junction_tables,
        "many_to_many_relationships": many_to_many,
        "warnings": [
            f"NON_UNIQUE_PARENT_KEY: {endpoint_label(edge['target_table'], edge['target_columns'])}"
            for edge in edges
            if (edge["metrics"].get("parent_duplicate_count") or 0) > 0
        ],
        "non_unique_parent_tables": non_unique_parent_tables,
    }


def _table_node(
    table_name: str,
    schema: Schema,
    catalog: CsvCatalog,
    profile: ProfileSummary,
) -> dict[str, Any]:
    table_schema = schema.tables[table_name]
    catalog_table = catalog.tables.get(table_name)
    table_profile = profile.tables.get(table_name)
    return {
        "table": table_name,
        "status": "mapped" if catalog_table else "missing_csv",
        "csv_path": str(catalog_table.csv_path) if catalog_table else "",
        "row_count": table_profile.row_count if table_profile else None,
        "column_count": table_profile.column_count if table_profile else len(table_schema.columns),
        "primary_key": list(table_schema.primary_key),
        "foreign_keys": [
            {
                "column": column.name,
                "parent_table": column.foreign_key.parent_table,
                "parent_column": column.foreign_key.parent_column,
            }
            for column in table_schema.columns.values()
            if column.foreign_key
        ],
        "referenced_by": [
            {
                "child_table": rel.child_table,
                "child_column": rel.child_column,
                "child_columns": child_columns(rel),
                "parent_column": rel.parent_column,
                "parent_columns": parent_columns(rel),
                "declared_cardinality": rel.declared_cardinality,
            }
            for rel in schema.relationships
            if rel.parent_table == table_name
        ],
    }


def _relationship_edge(
    rel: Relationship,
    catalog: CsvCatalog,
    relationship_summaries: list[dict[str, Any]],
    issues: list[Issue],
) -> dict[str, Any]:
    summary = _find_relationship_summary(rel, relationship_summaries)
    status, reason = _relationship_status(rel, catalog, summary)
    metrics = {
        "child_total": summary.get("child_total") if summary else None,
        "child_fk_null_count": summary.get("child_fk_null_count") if summary else None,
        "parent_duplicate_count": summary.get("parent_duplicate_count") if summary else None,
        "orphan_count": summary.get("orphan_count") if summary else None,
        "child_duplicate_count": summary.get("child_duplicate_count") if summary else None,
        "join_coverage": summary.get("join_coverage") if summary else None,
    }
    return {
        "id": relationship_id(rel),
        "source_table": rel.child_table,
        "source_column": rel.child_column,
        "source_columns": child_columns(rel),
        "target_table": rel.parent_table,
        "target_column": rel.parent_column,
        "target_columns": parent_columns(rel),
        "constraint_source": "dbml",
        "relationship_type": rel.relationship_type,
        "dbml_operator": rel.dbml_operator,
        "declared_cardinality": rel.declared_cardinality,
        "cardinality": _cardinality(summary),
        "observed_cardinality": _observed_cardinality(summary),
        "role": _relationship_role(summary),
        "confidence": 1.0,
        "status": status,
        "status_reason": reason,
        "metrics": metrics,
        "evidence_links": _relationship_issue_refs(rel, issues),
    }


def _relationship_status(
    rel: Relationship,
    catalog: CsvCatalog,
    summary: dict[str, Any] | None,
) -> tuple[str, str]:
    child = catalog.tables.get(rel.child_table)
    parent = catalog.tables.get(rel.parent_table)
    rel_child_columns = child_columns(rel)
    rel_parent_columns = parent_columns(rel)
    if not child:
        return "skipped", "child table CSV is missing"
    if not parent:
        return "skipped", "parent table CSV is missing"
    missing_child = [column for column in rel_child_columns if column not in child.columns]
    missing_parent = [column for column in rel_parent_columns if column not in parent.columns]
    if missing_child:
        return "skipped", "child FK column is missing"
    if missing_parent:
        return "skipped", "parent key column is missing"
    if not summary:
        return "skipped", "relationship check did not produce metrics"
    if int(summary.get("parent_duplicate_count") or 0) > 0:
        return "invalid", "parent key has duplicate values"
    if int(summary.get("orphan_count") or 0) > 0:
        return "invalid", "child table has orphan foreign keys"
    if (
        summary.get("declared_cardinality") == "ONE_TO_ONE"
        and int(summary.get("child_duplicate_count") or 0) > 0
    ):
        return "invalid", "child foreign key is not unique for one-to-one"
    if int(summary.get("child_fk_null_count") or 0) > 0:
        return "warning", "child foreign key has null or blank values"
    return "valid", "relationship passed direct FK checks"


def _cardinality(summary: dict[str, Any] | None) -> str:
    if not summary:
        return "UNKNOWN"
    if int(summary.get("parent_duplicate_count") or 0) > 0:
        return "UNKNOWN_INVALID_PARENT_KEY"
    return str(summary.get("declared_cardinality") or "MANY_TO_ONE")


def _observed_cardinality(summary: dict[str, Any] | None) -> str:
    if not summary:
        return "UNKNOWN"
    if int(summary.get("parent_duplicate_count") or 0) > 0:
        return "UNKNOWN_INVALID_PARENT_KEY"
    if int(summary.get("child_duplicate_count") or 0) > 0:
        return "MANY_TO_ONE"
    return "ONE_TO_ONE"


def _relationship_role(summary: dict[str, Any] | None) -> str:
    if not summary:
        return "unknown"
    if int(summary.get("parent_duplicate_count") or 0) > 0:
        return "blocked_by_non_unique_parent"
    if (
        summary.get("declared_cardinality") == "ONE_TO_ONE"
        and int(summary.get("child_duplicate_count") or 0) > 0
    ):
        return "blocked_by_non_unique_child"
    if summary.get("declared_cardinality") == "ONE_TO_ONE":
        return "one_to_one_child_to_parent"
    if summary.get("declared_cardinality") == "ONE_TO_MANY":
        return "one_to_many_declared_child_to_parent"
    return "child_to_parent"


def _find_relationship_summary(
    rel: Relationship,
    summaries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for summary in summaries:
        if (
            summary.get("child_table") == rel.child_table
            and summary.get("child_columns", [summary.get("child_column")]) == child_columns(rel)
            and summary.get("parent_table") == rel.parent_table
            and summary.get("parent_columns", [summary.get("parent_column")]) == parent_columns(rel)
        ):
            return summary
    return None


def _relationship_issue_refs(rel: Relationship, issues: list[Issue]) -> list[dict[str, Any]]:
    refs = []
    for issue in issues:
        if issue.issue_type not in RELATIONSHIP_ISSUE_TYPES:
            continue
        if issue.issue_type in {"FOREIGN_KEY_NULL", "ORPHAN_FOREIGN_KEY"}:
            matches = (
                issue.table == rel.child_table
                and issue.parent_table == rel.parent_table
                and bool(set(child_columns(rel)) & set(issue.columns))
            )
        elif issue.issue_type == "CHILD_RELATIONSHIP_DUPLICATE":
            matches = issue.table == rel.child_table and bool(set(child_columns(rel)) & set(issue.columns))
        else:
            matches = issue.table == rel.parent_table and bool(set(parent_columns(rel)) & set(issue.columns))
        if not matches:
            continue
        refs.append(
            {
                "issue_id": issue.issue_id,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "sample_bad_rows_path": issue.sample_bad_rows_path,
                "bad_count": issue.bad_count,
            }
        )
    return refs

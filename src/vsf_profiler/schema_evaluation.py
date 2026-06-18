from __future__ import annotations

from typing import Any

from vsf_profiler.csv_catalog import CsvCatalog
from vsf_profiler.models import ColumnSchema, Issue, Schema, TableSchema
from vsf_profiler.relationship_metadata import (
    child_columns,
    detect_junction_tables,
    parent_columns,
    relationship_id,
)


SCHEMA_ISSUE_TYPES = {
    "TABLE_MISSING",
    "COLUMN_MISSING",
    "EXTRA_COLUMN",
    "TYPE_CAST_INVALID",
    "REQUIRED_FIELD_NULL",
    "PRIMARY_KEY_NULL",
    "DUPLICATE_PRIMARY_KEY",
    "UNIQUE_DUPLICATE",
}


def build_schema_evaluation(
    *,
    schema: Schema,
    catalog: CsvCatalog,
    issues: list[Issue],
) -> dict[str, Any]:
    schema_issue_refs = [
        _issue_ref(issue) for issue in issues if issue.issue_type in SCHEMA_ISSUE_TYPES
    ]
    tables = [
        _table_evaluation(table_name, table_schema, catalog, issues)
        for table_name, table_schema in schema.tables.items()
    ]
    junction_tables = detect_junction_tables(schema)
    cardinality_counts = _relationship_cardinality_counts(schema)
    extra_csvs = [
        {"table": table_name, "csv_path": f"{table_name}.csv", "status": "extra_csv"}
        for table_name in catalog.extra_csvs
    ]
    return {
        "artifact": "schema_evaluation",
        "version": 1,
        "schema_meta": {
            "total_tables": len(schema.tables),
            "total_relationships": len(schema.relationships),
        },
        "summary": {
            "dbml_table_count": len(schema.tables),
            "mapped_table_count": len(catalog.tables),
            "missing_table_count": len(catalog.missing_tables),
            "extra_csv_count": len(catalog.extra_csvs),
            "schema_issue_count": len(schema_issue_refs),
            "composite_relationship_count": sum(
                1 for rel in schema.relationships if len(child_columns(rel)) > 1
            ),
            "junction_table_count": len(junction_tables),
            "relationship_cardinality_counts": cardinality_counts,
        },
        "missing_tables": list(catalog.missing_tables),
        "extra_csvs": extra_csvs,
        "tables": tables,
        "relationships": [
            {
                "id": relationship_id(rel),
                "child_table": rel.child_table,
                "child_column": rel.child_column,
                "child_columns": child_columns(rel),
                "parent_table": rel.parent_table,
                "parent_column": rel.parent_column,
                "parent_columns": parent_columns(rel),
                "relationship_type": rel.relationship_type,
                "dbml_operator": rel.dbml_operator,
                "declared_cardinality": rel.declared_cardinality,
                "status": "declared_in_schema",
                "confidence": 1.0,
            }
            for rel in schema.relationships
        ],
        "junction_tables": junction_tables,
        "schema_issues": schema_issue_refs,
    }


def _table_evaluation(
    table_name: str,
    table_schema: TableSchema,
    catalog: CsvCatalog,
    issues: list[Issue],
) -> dict[str, Any]:
    catalog_table = catalog.tables.get(table_name)
    csv_columns = catalog_table.columns if catalog_table else []
    dbml_columns = list(table_schema.columns)
    missing_columns = [column for column in dbml_columns if column not in csv_columns]
    extra_columns = [column for column in csv_columns if column not in table_schema.columns]
    table_issues = [
        _issue_ref(issue)
        for issue in issues
        if issue.issue_type in SCHEMA_ISSUE_TYPES and issue.table == table_name
    ]

    columns = [
        _dbml_column_evaluation(column_name, column_schema, csv_columns)
        for column_name, column_schema in table_schema.columns.items()
    ]
    columns.extend(_extra_csv_column_evaluation(column_name) for column_name in extra_columns)

    return {
        "table": table_name,
        "status": "mapped" if catalog_table else "missing_csv",
        "csv_path": _source_label(catalog_table) if catalog_table else "",
        "dbml_column_count": len(dbml_columns),
        "csv_column_count": len(csv_columns),
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "primary_key": list(table_schema.primary_key),
        "unique_constraints": list(table_schema.unique_constraints),
        "foreign_keys": [
            {
                "column": column.name,
                "parent_table": column.foreign_key.parent_table,
                "parent_column": column.foreign_key.parent_column,
            }
            for column in table_schema.columns.values()
            if column.foreign_key
        ],
        "columns": columns,
        "schema_issues": table_issues,
    }


def _dbml_column_evaluation(
    column_name: str,
    column: ColumnSchema,
    csv_columns: list[str],
) -> dict[str, Any]:
    foreign_key = None
    if column.foreign_key:
        foreign_key = {
            "parent_table": column.foreign_key.parent_table,
            "parent_column": column.foreign_key.parent_column,
        }
    return {
        "name": column_name,
        "in_dbml": True,
        "in_csv": column_name in csv_columns,
        "dbml_type": column.type,
        "is_pk": column.is_pk,
        "not_null": column.not_null,
        "unique": column.unique,
        "foreign_key": foreign_key,
    }


def _extra_csv_column_evaluation(column_name: str) -> dict[str, Any]:
    return {
        "name": column_name,
        "in_dbml": False,
        "in_csv": True,
        "dbml_type": None,
        "is_pk": False,
        "not_null": False,
        "unique": False,
        "foreign_key": None,
    }


def _issue_ref(issue: Issue) -> dict[str, Any]:
    return {
        "issue_id": issue.issue_id,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "table": issue.table,
        "columns": issue.columns,
        "bad_count": issue.bad_count,
        "sample_bad_rows_path": issue.sample_bad_rows_path,
    }


def _relationship_cardinality_counts(schema: Schema) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rel in schema.relationships:
        counts[rel.declared_cardinality] = counts.get(rel.declared_cardinality, 0) + 1
    return dict(sorted(counts.items()))


def _source_label(catalog_table) -> str:
    if catalog_table is None:
        return ""
    return catalog_table.source_name or str(catalog_table.csv_path)

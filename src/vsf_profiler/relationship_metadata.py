from __future__ import annotations

from itertools import combinations
from typing import Any

from vsf_profiler.models import Relationship, Schema


def child_columns(rel: Relationship) -> list[str]:
    return list(rel.child_columns or [rel.child_column])


def parent_columns(rel: Relationship) -> list[str]:
    return list(rel.parent_columns or [rel.parent_column])


def endpoint_label(table: str, columns: list[str]) -> str:
    if len(columns) == 1:
        return f"{table}.{columns[0]}"
    return f"{table}.({', '.join(columns)})"


def relationship_id(rel: Relationship) -> str:
    return f"{endpoint_label(rel.child_table, child_columns(rel))}->{endpoint_label(rel.parent_table, parent_columns(rel))}"


def detect_junction_tables(schema: Schema) -> list[dict[str, Any]]:
    junctions = []
    for table_name, table in schema.tables.items():
        outgoing = [rel for rel in schema.relationships if rel.child_table == table_name]
        if len(outgoing) < 2:
            continue

        fk_columns = [column for rel in outgoing for column in child_columns(rel)]
        fk_column_set = set(fk_columns)
        primary_key_set = set(table.primary_key)
        parent_tables = sorted({rel.parent_table for rel in outgoing})
        if len(parent_tables) < 2:
            continue
        if not primary_key_set or fk_column_set != primary_key_set:
            continue

        relationships = [
            {
                "relationship_id": relationship_id(rel),
                "child_columns": child_columns(rel),
                "parent_table": rel.parent_table,
                "parent_columns": parent_columns(rel),
                "declared_cardinality": rel.declared_cardinality,
            }
            for rel in sorted(outgoing, key=relationship_id)
        ]
        junctions.append(
            {
                "table": table_name,
                "relationship_type": "junction_table",
                "cardinality": "MANY_TO_MANY",
                "status": "detected",
                "primary_key": list(table.primary_key),
                "fk_columns": sorted(fk_column_set),
                "parent_tables": parent_tables,
                "relationships": relationships,
            }
        )
    return sorted(junctions, key=lambda item: item["table"])


def many_to_many_relationships(schema: Schema) -> list[dict[str, Any]]:
    relationships = []
    for junction in detect_junction_tables(schema):
        for left, right in combinations(junction["parent_tables"], 2):
            relationships.append(
                {
                    "relationship_type": "inferred_many_to_many",
                    "cardinality": "MANY_TO_MANY",
                    "status": "detected",
                    "left_table": left,
                    "right_table": right,
                    "junction_table": junction["table"],
                }
            )
    return sorted(
        relationships,
        key=lambda item: (item["junction_table"], item["left_table"], item["right_table"]),
    )

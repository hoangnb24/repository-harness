from __future__ import annotations

import duckdb

from vsf_profiler.csv_catalog import CsvCatalog
from vsf_profiler.duckdb_utils import csv_relation, non_empty_expr, null_or_empty_expr, quote_ident, run_scalar
from vsf_profiler.issue_catalog import IssueCatalog
from vsf_profiler.models import ProfileSummary, Relationship, Schema


def run_relationship_checks(
    *,
    con: duckdb.DuckDBPyConnection,
    schema: Schema,
    catalog: CsvCatalog,
    profile: ProfileSummary,
    issues: IssueCatalog,
) -> list[dict]:
    summaries: list[dict] = []
    for rel in schema.relationships:
        summary = _check_relationship(con, catalog, profile, issues, rel)
        if summary:
            summaries.append(summary)
    return summaries


def _check_relationship(
    con: duckdb.DuckDBPyConnection,
    catalog: CsvCatalog,
    profile: ProfileSummary,
    issues: IssueCatalog,
    rel: Relationship,
) -> dict | None:
    child = catalog.tables.get(rel.child_table)
    parent = catalog.tables.get(rel.parent_table)
    child_profile = profile.tables.get(rel.child_table)
    if not child or not parent or not child_profile:
        return None
    child_columns = _child_columns(rel)
    parent_columns = _parent_columns(rel)
    if any(column not in child.columns for column in child_columns) or any(
        column not in parent.columns for column in parent_columns
    ):
        return None

    child_rel = csv_relation(child.csv_path)
    parent_rel = csv_relation(parent.csv_path)
    total = child_profile.row_count

    child_cols = [quote_ident(column) for column in child_columns]
    parent_cols = [quote_ident(column) for column in parent_columns]
    child_non_empty = _all_non_empty(child_cols)
    parent_non_empty = _all_non_empty(parent_cols)
    child_non_empty_qualified = _all_non_empty([f"c.{column}" for column in child_cols])

    fk_null_condition = _any_null_or_empty(child_cols)
    null_count = int(
        run_scalar(con, f"SELECT COUNT(*) FROM {child_rel} WHERE {fk_null_condition}", 0)
    )
    issues.add_count_issue(
        issue_type="FOREIGN_KEY_NULL",
        severity="P3",
        table=rel.child_table,
        columns=child_columns,
        parent_table=rel.parent_table,
        parent_columns=parent_columns,
        total_count=total,
        count_sql=f"SELECT COUNT(*) FROM {child_rel} WHERE {fk_null_condition}",
        sample_sql=f"SELECT * FROM {child_rel} WHERE {fk_null_condition} LIMIT 50",
    )

    dup_parent = (
        f"SELECT {_select_columns(parent_cols)} FROM {parent_rel} "
        f"WHERE {parent_non_empty} "
        f"GROUP BY {_select_columns(parent_cols)} HAVING COUNT(*) > 1"
    )
    parent_dup_count_sql = (
        f"SELECT COUNT(*) FROM {parent_rel} p JOIN ({dup_parent}) d "
        f"ON {_join_conditions('p', parent_columns, 'd', parent_columns)}"
    )
    parent_total = profile.tables.get(rel.parent_table).row_count if rel.parent_table in profile.tables else 0
    issues.add_count_issue(
        issue_type="PARENT_KEY_DUPLICATE",
        severity="P1",
        table=rel.parent_table,
        columns=parent_columns,
        total_count=parent_total,
        count_sql=parent_dup_count_sql,
        sample_sql=(
            f"SELECT p.* FROM {parent_rel} p JOIN ({dup_parent}) d "
            f"ON {_join_conditions('p', parent_columns, 'd', parent_columns)} LIMIT 50"
        ),
        sample_key_sql=f"SELECT DISTINCT {_key_expr(parent_cols)} FROM ({dup_parent}) LIMIT 10",
    )

    parent_distinct = (
        f"SELECT DISTINCT {_aliased_parent_keys(parent_cols)} FROM {parent_rel} "
        f"WHERE {parent_non_empty}"
    )
    orphan_condition = f"{child_non_empty_qualified} AND p.parent_key_0 IS NULL"
    orphan_sql = (
        f"SELECT COUNT(*) FROM {child_rel} c "
        f"LEFT JOIN ({parent_distinct}) p ON {_parent_key_join_conditions(child_columns)} "
        f"WHERE {orphan_condition}"
    )
    orphan_count = int(run_scalar(con, orphan_sql, 0))
    issues.add_issue(
        issue_type="ORPHAN_FOREIGN_KEY",
        severity="P1",
        table=rel.child_table,
        columns=child_columns,
        parent_table=rel.parent_table,
        parent_columns=parent_columns,
        bad_count=orphan_count,
        total_count=total,
        evidence_sql=orphan_sql,
        sample_sql=(
            f"SELECT c.* FROM {child_rel} c "
            f"LEFT JOIN ({parent_distinct}) p ON {_parent_key_join_conditions(child_columns)} "
            f"WHERE {orphan_condition} LIMIT 50"
        ),
        sample_key_sql=(
            f"SELECT DISTINCT {_key_expr([f'c.{column}' for column in child_cols])} FROM {child_rel} c "
            f"LEFT JOIN ({parent_distinct}) p ON {_parent_key_join_conditions(child_columns)} "
            f"WHERE {orphan_condition} LIMIT 10"
        ),
    )

    non_null_child = int(
        run_scalar(con, f"SELECT COUNT(*) FROM {child_rel} WHERE {child_non_empty}", 0)
    )
    coverage = 0.0 if non_null_child == 0 else round((non_null_child - orphan_count) / non_null_child, 6)
    dup_child = (
        f"SELECT {_select_columns(child_cols)} FROM {child_rel} "
        f"WHERE {child_non_empty} "
        f"GROUP BY {_select_columns(child_cols)} HAVING COUNT(*) > 1"
    )
    child_duplicate_count_sql = (
        f"SELECT COUNT(*) FROM {child_rel} c JOIN ({dup_child}) d "
        f"ON {_join_conditions('c', child_columns, 'd', child_columns)}"
    )
    child_duplicate_count = int(run_scalar(con, child_duplicate_count_sql, 0))
    if rel.declared_cardinality == "ONE_TO_ONE":
        issues.add_count_issue(
            issue_type="CHILD_RELATIONSHIP_DUPLICATE",
            severity="P1",
            table=rel.child_table,
            columns=child_columns,
            parent_table=rel.parent_table,
            parent_columns=parent_columns,
            total_count=total,
            count_sql=child_duplicate_count_sql,
            sample_sql=(
                f"SELECT c.* FROM {child_rel} c JOIN ({dup_child}) d "
                f"ON {_join_conditions('c', child_columns, 'd', child_columns)} LIMIT 50"
            ),
            sample_key_sql=f"SELECT DISTINCT {_key_expr(child_cols)} FROM ({dup_child}) LIMIT 10",
        )

    return {
        "child_table": rel.child_table,
        "child_column": rel.child_column,
        "child_columns": child_columns,
        "parent_table": rel.parent_table,
        "parent_column": rel.parent_column,
        "parent_columns": parent_columns,
        "dbml_operator": rel.dbml_operator,
        "declared_cardinality": rel.declared_cardinality,
        "relationship_type": rel.relationship_type,
        "child_total": total,
        "child_fk_null_count": null_count,
        "parent_duplicate_count": int(run_scalar(con, parent_dup_count_sql, 0)),
        "orphan_count": orphan_count,
        "child_duplicate_count": child_duplicate_count,
        "join_coverage": coverage,
    }


def _child_columns(rel: Relationship) -> list[str]:
    return list(rel.child_columns or [rel.child_column])


def _parent_columns(rel: Relationship) -> list[str]:
    return list(rel.parent_columns or [rel.parent_column])


def _all_non_empty(columns: list[str]) -> str:
    return " AND ".join(non_empty_expr(column) for column in columns)


def _any_null_or_empty(columns: list[str]) -> str:
    return " OR ".join(null_or_empty_expr(column) for column in columns)


def _select_columns(columns: list[str]) -> str:
    return ", ".join(columns)


def _join_conditions(
    left_alias: str,
    left_columns: list[str],
    right_alias: str,
    right_columns: list[str],
) -> str:
    return " AND ".join(
        f"{left_alias}.{quote_ident(left)} = {right_alias}.{quote_ident(right)}"
        for left, right in zip(left_columns, right_columns, strict=False)
    )


def _aliased_parent_keys(parent_cols: list[str]) -> str:
    return ", ".join(
        f"{column} AS parent_key_{index}"
        for index, column in enumerate(parent_cols)
    )


def _parent_key_join_conditions(child_columns: list[str]) -> str:
    return " AND ".join(
        f"c.{quote_ident(child_column)} = p.parent_key_{index}"
        for index, child_column in enumerate(child_columns)
    )


def _key_expr(columns: list[str]) -> str:
    return " || '|' || ".join(f"CAST({column} AS VARCHAR)" for column in columns)

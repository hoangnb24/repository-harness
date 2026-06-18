from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import yaml

from vsf_profiler.csv_catalog import CsvCatalog
from vsf_profiler.duckdb_utils import (
    csv_relation,
    non_empty_expr,
    null_or_empty_expr,
    quote_ident,
    sql_literal,
    try_cast_expr,
)
from vsf_profiler.issue_catalog import IssueCatalog
from vsf_profiler.models import ProfileSummary, Schema, TableSchema


PLACEHOLDER_TOKENS = ["N/A", "NA", "unknown", ".", "-", "null", "None"]


def run_quality_checks(
    *,
    con: duckdb.DuckDBPyConnection,
    schema: Schema,
    catalog: CsvCatalog,
    profile: ProfileSummary,
    issues: IssueCatalog,
    rules_path: str | Path | None = None,
) -> None:
    _schema_checks(schema, catalog, profile, issues)
    _dbml_value_checks(con, schema, catalog, profile, issues)
    _numeric_outlier_checks(catalog, profile, issues)
    _yaml_rules(con, catalog, profile, issues, rules_path)


def _schema_checks(
    schema: Schema,
    catalog: CsvCatalog,
    profile: ProfileSummary,
    issues: IssueCatalog,
) -> None:
    for table_name in catalog.missing_tables:
        issues.add_issue(
            issue_type="TABLE_MISSING",
            severity="P0",
            table=table_name,
            columns=[],
            bad_count=1,
            total_count=1,
            evidence_sql=f"-- Missing CSV for DBML table {table_name}",
        )

    for table_name, table_schema in schema.tables.items():
        catalog_table = catalog.tables.get(table_name)
        if not catalog_table:
            continue
        table_profile = profile.tables[table_name]
        csv_columns = set(catalog_table.columns)
        for column_name in table_schema.columns:
            if column_name not in csv_columns:
                issues.add_issue(
                    issue_type="COLUMN_MISSING",
                    severity="P0",
                    table=table_name,
                    columns=[column_name],
                    bad_count=table_profile.row_count,
                    total_count=table_profile.row_count,
                    evidence_sql=f"-- Missing CSV column {table_name}.{column_name}",
                )
        for column_name in catalog_table.columns:
            if column_name not in table_schema.columns:
                issues.add_issue(
                    issue_type="EXTRA_COLUMN",
                    severity="P3",
                    table=table_name,
                    columns=[column_name],
                    bad_count=table_profile.row_count,
                    total_count=table_profile.row_count,
                    evidence_sql=f"-- Extra CSV column {table_name}.{column_name}",
                )


def _dbml_value_checks(
    con: duckdb.DuckDBPyConnection,
    schema: Schema,
    catalog: CsvCatalog,
    profile: ProfileSummary,
    issues: IssueCatalog,
) -> None:
    for table_name, table_schema in schema.tables.items():
        catalog_table = catalog.tables.get(table_name)
        table_profile = profile.tables.get(table_name)
        if not catalog_table or not table_profile:
            continue

        relation = csv_relation(catalog_table.csv_path)
        for column_name, column_schema in table_schema.columns.items():
            if column_name not in catalog_table.columns:
                continue
            col = quote_ident(column_name)
            total = table_profile.row_count

            cast_expr = try_cast_expr(col, column_schema.type)
            if cast_expr:
                condition = f"{non_empty_expr(col)} AND {cast_expr} IS NULL"
                issues.add_count_issue(
                    issue_type="TYPE_CAST_INVALID",
                    severity="P1",
                    table=table_name,
                    columns=[column_name],
                    total_count=total,
                    count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
                    sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
                    sample_key_sql=f"SELECT DISTINCT {col} FROM {relation} WHERE {condition} LIMIT 10",
                )

            if column_schema.not_null:
                condition = null_or_empty_expr(col)
                issues.add_count_issue(
                    issue_type="REQUIRED_FIELD_NULL",
                    severity="P1",
                    table=table_name,
                    columns=[column_name],
                    total_count=total,
                    count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
                    sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
                )

            if column_schema.is_pk:
                condition = null_or_empty_expr(col)
                issues.add_count_issue(
                    issue_type="PRIMARY_KEY_NULL",
                    severity="P0",
                    table=table_name,
                    columns=[column_name],
                    total_count=total,
                    count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
                    sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
                )

            if column_schema.unique:
                _duplicate_key_issue(
                    issues=issues,
                    table_name=table_name,
                    relation=relation,
                    columns=[column_name],
                    total=total,
                    issue_type="UNIQUE_DUPLICATE",
                    severity="P1",
                )

            if column_schema.type.lower().split("(")[0] in {"varchar", "text", "string", "char"}:
                _text_quality_checks(issues, table_name, relation, column_name, total)

        for unique_columns in table_schema.unique_constraints:
            if all(column_name in catalog_table.columns for column_name in unique_columns):
                _duplicate_key_issue(
                    issues=issues,
                    table_name=table_name,
                    relation=relation,
                    columns=unique_columns,
                    total=table_profile.row_count,
                    issue_type="UNIQUE_DUPLICATE",
                    severity="P1",
                )

        pk_columns = _primary_key_columns(table_schema)
        if pk_columns:
            _duplicate_key_issue(
                issues=issues,
                table_name=table_name,
                relation=relation,
                columns=pk_columns,
                total=table_profile.row_count,
                issue_type="DUPLICATE_PRIMARY_KEY",
                severity="P0",
            )


def _primary_key_columns(table_schema: TableSchema) -> list[str]:
    if table_schema.primary_key:
        return table_schema.primary_key
    return [column.name for column in table_schema.columns.values() if column.is_pk]


def _numeric_outlier_checks(
    catalog: CsvCatalog,
    profile: ProfileSummary,
    issues: IssueCatalog,
) -> None:
    for table_name, catalog_table in catalog.tables.items():
        table_profile = profile.tables.get(table_name)
        if not table_profile:
            continue
        relation = csv_relation(catalog_table.csv_path)
        for column_name, column_profile in table_profile.columns.items():
            outliers = column_profile.outliers
            if outliers is None or outliers.outlier_count <= 0:
                continue
            if outliers.lower_fence is None or outliers.upper_fence is None:
                continue
            col = quote_ident(column_name)
            numeric = f"try_cast({col} AS DOUBLE)"
            lower = _numeric_literal(outliers.lower_fence)
            upper = _numeric_literal(outliers.upper_fence)
            condition = (
                f"{numeric} IS NOT NULL "
                f"AND ({numeric} < {lower} OR {numeric} > {upper})"
            )
            issues.add_count_issue(
                issue_type="NUMERIC_OUTLIER",
                severity="P3",
                table=table_name,
                columns=[column_name],
                total_count=table_profile.row_count,
                count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
                sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
                sample_key_sql=f"SELECT DISTINCT {col} FROM {relation} WHERE {condition} LIMIT 10",
            )


def _numeric_literal(value: float) -> str:
    return format(float(value), ".17g")


def _duplicate_key_issue(
    *,
    issues: IssueCatalog,
    table_name: str,
    relation: str,
    columns: list[str],
    total: int,
    issue_type: str,
    severity: str,
) -> None:
    quoted_cols = [quote_ident(col) for col in columns]
    select_cols = ", ".join(quoted_cols)
    non_empty = " AND ".join(non_empty_expr(col) for col in quoted_cols)
    join_conditions = " AND ".join(f"t.{col} = d.{col}" for col in quoted_cols)
    dup = (
        f"SELECT {select_cols} FROM {relation} "
        f"WHERE {non_empty} GROUP BY {select_cols} HAVING COUNT(*) > 1"
    )
    count_sql = f"SELECT COUNT(*) FROM {relation} t JOIN ({dup}) d ON {join_conditions}"
    sample_sql = f"SELECT t.* FROM {relation} t JOIN ({dup}) d ON {join_conditions} LIMIT 50"
    key_expr = " || '|' || ".join(f"CAST({col} AS VARCHAR)" for col in quoted_cols)
    key_sql = f"SELECT DISTINCT {key_expr} FROM ({dup}) LIMIT 10"
    issues.add_count_issue(
        issue_type=issue_type,
        severity=severity,
        table=table_name,
        columns=columns,
        total_count=total,
        count_sql=count_sql,
        sample_sql=sample_sql,
        sample_key_sql=key_sql,
    )


def _text_quality_checks(
    issues: IssueCatalog,
    table_name: str,
    relation: str,
    column_name: str,
    total: int,
) -> None:
    col = quote_ident(column_name)
    empty_condition = f"{col} IS NOT NULL AND trim(CAST({col} AS VARCHAR)) = ''"
    issues.add_count_issue(
        issue_type="EMPTY_STRING",
        severity="P3",
        table=table_name,
        columns=[column_name],
        total_count=total,
        count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {empty_condition}",
        sample_sql=f"SELECT * FROM {relation} WHERE {empty_condition} LIMIT 50",
    )

    placeholders = ", ".join(sql_literal(token.lower()) for token in PLACEHOLDER_TOKENS)
    placeholder_condition = f"lower(trim(CAST({col} AS VARCHAR))) IN ({placeholders})"
    issues.add_count_issue(
        issue_type="INVALID_PLACEHOLDER_TOKEN",
        severity="P3",
        table=table_name,
        columns=[column_name],
        total_count=total,
        count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {placeholder_condition}",
        sample_sql=f"SELECT * FROM {relation} WHERE {placeholder_condition} LIMIT 50",
        sample_key_sql=f"SELECT DISTINCT {col} FROM {relation} WHERE {placeholder_condition} LIMIT 10",
    )


def _yaml_rules(
    con: duckdb.DuckDBPyConnection,
    catalog: CsvCatalog,
    profile: ProfileSummary,
    issues: IssueCatalog,
    rules_path: str | Path | None,
) -> None:
    if not rules_path:
        return
    path = Path(rules_path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file does not exist: {path}")
    loaded = yaml.safe_load(path.read_text()) or {}
    rules_by_table = loaded.get("rules", {})
    if not isinstance(rules_by_table, dict):
        raise ValueError("rules.yaml must contain a top-level 'rules' mapping")

    for table_name, rules in rules_by_table.items():
        catalog_table = catalog.tables.get(table_name)
        table_profile = profile.tables.get(table_name)
        if not catalog_table or not table_profile:
            continue
        relation = csv_relation(catalog_table.csv_path)
        for rule in rules or []:
            _run_yaml_rule(con, issues, relation, table_name, table_profile.row_count, rule)


def _run_yaml_rule(
    con: duckdb.DuckDBPyConnection,
    issues: IssueCatalog,
    relation: str,
    table_name: str,
    total: int,
    rule: dict[str, Any],
) -> None:
    rule_type = str(rule.get("type", "")).lower()
    severity = str(rule.get("severity", "P2"))
    if rule_type == "range":
        _range_rule(issues, relation, table_name, total, rule, severity)
    elif rule_type == "accepted_values":
        _accepted_values_rule(issues, relation, table_name, total, rule, severity)
    elif rule_type == "regex":
        _regex_rule(issues, relation, table_name, total, rule, severity)
    elif rule_type == "expression":
        _expression_rule(issues, relation, table_name, total, rule, severity)
    else:
        raise ValueError(f"Unsupported YAML rule type for {table_name}: {rule_type}")


def _range_rule(
    issues: IssueCatalog,
    relation: str,
    table_name: str,
    total: int,
    rule: dict[str, Any],
    severity: str,
) -> None:
    column = str(rule["column"])
    col = quote_ident(column)
    numeric = f"try_cast({col} AS DOUBLE)"
    bounds: list[str] = []
    if "min" in rule:
        bounds.append(f"{numeric} < {float(rule['min'])}")
    if "max" in rule:
        bounds.append(f"{numeric} > {float(rule['max'])}")
    condition = f"{non_empty_expr(col)} AND ({' OR '.join(bounds)})"
    issue_type = "VALUE_OUT_OF_RANGE"
    if float(rule.get("min", -1)) == 0.0 and "max" not in rule:
        issue_type = "NEGATIVE_VALUE_NOT_ALLOWED"
    issues.add_count_issue(
        issue_type=issue_type,
        severity=severity,
        table=table_name,
        columns=[column],
        total_count=total,
        count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
        sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
        sample_key_sql=f"SELECT DISTINCT {col} FROM {relation} WHERE {condition} LIMIT 10",
    )


def _accepted_values_rule(
    issues: IssueCatalog,
    relation: str,
    table_name: str,
    total: int,
    rule: dict[str, Any],
    severity: str,
) -> None:
    column = str(rule["column"])
    values = [str(value) for value in rule.get("values", [])]
    col = quote_ident(column)
    accepted = ", ".join(sql_literal(value) for value in values)
    condition = f"{non_empty_expr(col)} AND CAST({col} AS VARCHAR) NOT IN ({accepted})"
    issues.add_count_issue(
        issue_type="ACCEPTED_VALUE_VIOLATION",
        severity=severity,
        table=table_name,
        columns=[column],
        total_count=total,
        count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
        sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
        sample_key_sql=f"SELECT DISTINCT {col} FROM {relation} WHERE {condition} LIMIT 10",
    )


def _regex_rule(
    issues: IssueCatalog,
    relation: str,
    table_name: str,
    total: int,
    rule: dict[str, Any],
    severity: str,
) -> None:
    column = str(rule["column"])
    pattern = str(rule["pattern"])
    col = quote_ident(column)
    condition = f"{non_empty_expr(col)} AND NOT regexp_matches(CAST({col} AS VARCHAR), {sql_literal(pattern)})"
    issues.add_count_issue(
        issue_type="REGEX_MISMATCH",
        severity=severity,
        table=table_name,
        columns=[column],
        total_count=total,
        count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
        sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
    )


def _expression_rule(
    issues: IssueCatalog,
    relation: str,
    table_name: str,
    total: int,
    rule: dict[str, Any],
    severity: str,
) -> None:
    expression = str(rule["expression"])
    where = str(rule.get("where", "TRUE"))
    columns = [str(col) for col in rule.get("columns", [])]
    condition = f"({where}) AND NOT ({expression})"
    issue_type = "DATE_ORDER_INVALID" if "date" in expression.lower() or "timestamp" in expression.lower() else "EXPRESSION_RULE_FAILED"
    if "DELIVERED_AFTER_PURCHASE" in str(rule.get("id", "")):
        issue_type = "DATE_ORDER_INVALID"
    issues.add_count_issue(
        issue_type=issue_type,
        severity=severity,
        table=table_name,
        columns=columns,
        total_count=total,
        count_sql=f"SELECT COUNT(*) FROM {relation} WHERE {condition}",
        sample_sql=f"SELECT * FROM {relation} WHERE {condition} LIMIT 50",
    )

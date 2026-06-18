from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


NUMERIC_TYPES = {
    "int",
    "integer",
    "bigint",
    "smallint",
    "tinyint",
    "float",
    "double",
    "decimal",
    "numeric",
    "real",
}
INTEGER_TYPES = {"int", "integer", "bigint", "smallint", "tinyint"}
FLOAT_TYPES = {"float", "double", "decimal", "numeric", "real"}
TIMESTAMP_TYPES = {"timestamp", "datetime", "date"}
TEXT_TYPES = {"varchar", "text", "string", "char"}


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database=":memory:")


def sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def csv_relation(path: Path) -> str:
    return (
        "read_csv_auto("
        f"{sql_literal(path)}, "
        "header=true, "
        "all_varchar=true, "
        "ignore_errors=true, "
        "null_padding=true, "
        "parallel=false"
        ")"
    )


def dbml_type_family(dbml_type: str | None) -> str:
    if not dbml_type:
        return "text"
    normalized = dbml_type.lower().split("(")[0].strip()
    if normalized in INTEGER_TYPES:
        return "integer"
    if normalized in FLOAT_TYPES:
        return "float"
    if normalized in TIMESTAMP_TYPES:
        return "timestamp"
    if normalized in TEXT_TYPES:
        return "text"
    return "text"


def duckdb_cast_type(dbml_type: str | None) -> str | None:
    family = dbml_type_family(dbml_type)
    if family == "integer":
        return "BIGINT"
    if family == "float":
        return "DOUBLE"
    if family == "timestamp":
        return "TIMESTAMP"
    return None


def non_empty_expr(column_sql: str) -> str:
    return f"{column_sql} IS NOT NULL AND trim(CAST({column_sql} AS VARCHAR)) <> ''"


def null_or_empty_expr(column_sql: str) -> str:
    return f"{column_sql} IS NULL OR trim(CAST({column_sql} AS VARCHAR)) = ''"


def try_cast_expr(column_sql: str, dbml_type: str | None) -> str | None:
    cast_type = duckdb_cast_type(dbml_type)
    if not cast_type:
        return None
    return f"try_cast({column_sql} AS {cast_type})"


def run_scalar(con: duckdb.DuckDBPyConnection, sql: str, default: int | float | str | None = 0):
    row = con.execute(sql).fetchone()
    if not row:
        return default
    return default if row[0] is None else row[0]


def fetch_bounded_df(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    *,
    max_rows: int,
    max_columns: int,
) -> pd.DataFrame:
    if max_rows <= 0:
        raise ValueError("max_rows must be greater than zero")
    if max_columns <= 0:
        raise ValueError("max_columns must be greater than zero")

    limited_sql = f"SELECT * FROM ({_strip_sql_terminator(sql)}) AS bounded_df LIMIT {int(max_rows)}"
    cursor = con.execute(limited_sql)
    column_count = len(cursor.description or [])
    if column_count > max_columns:
        raise ValueError(
            f"Bounded dataframe has {column_count} columns, exceeding max_columns={max_columns}"
        )
    return cursor.fetchdf()


def safe_rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(part) / float(total)


def _strip_sql_terminator(sql: str) -> str:
    return sql.strip().removesuffix(";")

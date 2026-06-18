from __future__ import annotations

from typing import Any

import duckdb

from vsf_profiler.csv_catalog import CsvCatalog
from vsf_profiler.duckdb_utils import (
    connect,
    csv_relation,
    dbml_type_family,
    non_empty_expr,
    null_or_empty_expr,
    quote_ident,
    run_scalar,
    safe_rate,
    try_cast_expr,
)
from vsf_profiler.models import ColumnProfile, ProfileSummary, Schema, TableProfile


def profile_dataset(
    schema: Schema,
    catalog: CsvCatalog,
    con: duckdb.DuckDBPyConnection | None = None,
) -> ProfileSummary:
    if con is not None:
        return _profile_dataset_with_connection(con, schema, catalog)
    owned = connect()
    try:
        return _profile_dataset_with_connection(owned, schema, catalog)
    finally:
        owned.close()


def _profile_dataset_with_connection(
    con: duckdb.DuckDBPyConnection,
    schema: Schema,
    catalog: CsvCatalog,
) -> ProfileSummary:
    summary = ProfileSummary(
        catalog=catalog.model_dump(mode="json"),
        relationships=[rel.model_dump() for rel in schema.relationships],
    )
    for table_name, catalog_table in catalog.tables.items():
        relation = csv_relation(catalog_table.csv_path)
        row_count = int(run_scalar(con, f"SELECT COUNT(*) FROM {relation}", 0))
        table_profile = TableProfile(
            table=table_name,
            row_count=row_count,
            column_count=len(catalog_table.columns),
            file_size_mb=catalog_table.file_size_mb,
        )

        table_schema = schema.tables.get(table_name)
        for column_name in catalog_table.columns:
            expected_type = None
            if table_schema and column_name in table_schema.columns:
                expected_type = table_schema.columns[column_name].type
            table_profile.columns[column_name] = _profile_column(
                con=con,
                relation=relation,
                column_name=column_name,
                expected_type=expected_type,
                row_count=row_count,
            )
        summary.tables[table_name] = table_profile
    return summary


def _profile_column(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    column_name: str,
    expected_type: str | None,
    row_count: int,
) -> ColumnProfile:
    col = quote_ident(column_name)
    null_count = int(
        run_scalar(
            con,
            f"SELECT COUNT(*) FROM {relation} WHERE {null_or_empty_expr(col)}",
            0,
        )
    )
    distinct_count = int(
        run_scalar(
            con,
            f"SELECT COUNT(DISTINCT {col}) FROM {relation} WHERE {non_empty_expr(col)}",
            0,
        )
    )
    inferred_type = _infer_type(con, relation, col)
    invalid_cast_count = _invalid_cast_count(con, relation, col, expected_type)
    stats = _column_stats(con, relation, col, expected_type, inferred_type)
    top_10 = _top_values(con, relation, col)

    return ColumnProfile(
        name=column_name,
        expected_type_from_dbml=expected_type,
        inferred_type=inferred_type,
        null_count=null_count,
        null_rate=round(null_count / row_count, 6) if row_count else 0.0,
        distinct_count=distinct_count,
        top_10_values=top_10,
        invalid_cast_count=invalid_cast_count,
        **stats,
    )


def _infer_type(con: duckdb.DuckDBPyConnection, relation: str, col: str) -> str:
    sql = f"""
    SELECT
      COUNT(*) FILTER (WHERE {non_empty_expr(col)}) AS non_empty,
      COUNT(*) FILTER (WHERE {non_empty_expr(col)} AND try_cast({col} AS BIGINT) IS NOT NULL) AS int_ok,
      COUNT(*) FILTER (WHERE {non_empty_expr(col)} AND try_cast({col} AS DOUBLE) IS NOT NULL) AS float_ok,
      COUNT(*) FILTER (WHERE {non_empty_expr(col)} AND try_cast({col} AS TIMESTAMP) IS NOT NULL) AS ts_ok
    FROM {relation}
    """
    non_empty, int_ok, float_ok, ts_ok = con.execute(sql).fetchone()
    non_empty = int(non_empty or 0)
    if non_empty == 0:
        return "empty"
    if int(int_ok or 0) == non_empty:
        return "int"
    if int(float_ok or 0) == non_empty:
        return "float"
    if int(ts_ok or 0) == non_empty:
        return "timestamp"
    return "varchar"


def _invalid_cast_count(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    col: str,
    expected_type: str | None,
) -> int:
    cast_expr = try_cast_expr(col, expected_type)
    if not cast_expr:
        return 0
    sql = (
        f"SELECT COUNT(*) FROM {relation} "
        f"WHERE {non_empty_expr(col)} AND {cast_expr} IS NULL"
    )
    return int(run_scalar(con, sql, 0))


def _column_stats(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    col: str,
    expected_type: str | None,
    inferred_type: str,
) -> dict[str, Any]:
    family = dbml_type_family(expected_type) if expected_type else inferred_type
    if family in {"integer", "float"} or inferred_type in {"int", "float"}:
        numeric = f"try_cast({col} AS DOUBLE)"
        sql = f"""
        SELECT
          MIN({numeric}) AS min_value,
          MAX({numeric}) AS max_value,
          AVG({numeric}) AS mean_value,
          STDDEV_SAMP({numeric}) AS std_value,
          quantile_cont({numeric}, 0.25) AS p25_value,
          quantile_cont({numeric}, 0.50) AS p50_value,
          quantile_cont({numeric}, 0.75) AS p75_value,
          quantile_cont({numeric}, 0.95) AS p95_value,
          quantile_cont({numeric}, 0.99) AS p99_value,
          COUNT({numeric}) AS numeric_count
        FROM {relation}
        WHERE {numeric} IS NOT NULL
        """
        row = con.execute(sql).fetchone()
        stats = {
            "min": _jsonable(row[0]),
            "max": _jsonable(row[1]),
            "mean": _jsonable(row[2]),
            "std": _jsonable(row[3]),
            "p25": _jsonable(row[4]),
            "p50": _jsonable(row[5]),
            "p75": _jsonable(row[6]),
            "p95": _jsonable(row[7]),
            "p99": _jsonable(row[8]),
        }
        numeric_count = int(row[9] or 0)
        stats["outliers"] = _iqr_outlier_profile(
            con=con,
            relation=relation,
            numeric=numeric,
            q1=stats["p25"],
            q3=stats["p75"],
            numeric_count=numeric_count,
        )
        return stats

    if family == "timestamp" or inferred_type == "timestamp":
        ts = f"try_cast({col} AS TIMESTAMP)"
        sql = f"SELECT MIN({ts}), MAX({ts}) FROM {relation} WHERE {ts} IS NOT NULL"
        row = con.execute(sql).fetchone()
        return {"min": _jsonable(row[0]), "max": _jsonable(row[1])}

    return {}


def _iqr_outlier_profile(
    *,
    con: duckdb.DuckDBPyConnection,
    relation: str,
    numeric: str,
    q1: Any,
    q3: Any,
    numeric_count: int,
) -> dict[str, Any]:
    if q1 is None or q3 is None or numeric_count <= 0:
        return {
            "method": "iqr",
            "q1": None,
            "q3": None,
            "iqr": None,
            "lower_fence": None,
            "upper_fence": None,
            "outlier_count": 0,
            "outlier_rate": 0.0,
        }
    q1_value = float(q1)
    q3_value = float(q3)
    iqr = q3_value - q1_value
    lower_fence = q1_value - (1.5 * iqr)
    upper_fence = q3_value + (1.5 * iqr)
    condition = f"{numeric} IS NOT NULL AND ({numeric} < {lower_fence} OR {numeric} > {upper_fence})"
    outlier_count = int(run_scalar(con, f"SELECT COUNT(*) FROM {relation} WHERE {condition}", 0))
    return {
        "method": "iqr",
        "q1": _jsonable(q1_value),
        "q3": _jsonable(q3_value),
        "iqr": _jsonable(iqr),
        "lower_fence": _jsonable(lower_fence),
        "upper_fence": _jsonable(upper_fence),
        "outlier_count": outlier_count,
        "outlier_rate": round(safe_rate(outlier_count, numeric_count), 6),
    }


def _top_values(con: duckdb.DuckDBPyConnection, relation: str, col: str) -> list[dict[str, Any]]:
    sql = f"""
    SELECT CAST({col} AS VARCHAR) AS value, COUNT(*) AS count
    FROM {relation}
    GROUP BY 1
    ORDER BY count DESC, value
    LIMIT 10
    """
    rows = con.execute(sql).fetchall()
    return [{"value": "" if value is None else str(value), "count": int(count)} for value, count in rows]


def _jsonable(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 6)
    return value

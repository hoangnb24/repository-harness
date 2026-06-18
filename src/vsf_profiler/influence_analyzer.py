from __future__ import annotations

import duckdb
import pandas as pd

from vsf_profiler.csv_catalog import CsvCatalog
from vsf_profiler.duckdb_utils import csv_relation, fetch_bounded_df, quote_ident
from vsf_profiler.models import InfluenceFeature, InfluenceResult, Schema


MAX_ANALYSIS_ROWS = 100_000
MAX_FEATURE_COLUMNS = 50
MAX_REPORTED_FEATURES = 20


def analyze_influence(
    *,
    con: duckdb.DuckDBPyConnection,
    schema: Schema,
    catalog: CsvCatalog,
    target: str | None,
    max_analysis_rows: int = MAX_ANALYSIS_ROWS,
    max_feature_columns: int = MAX_FEATURE_COLUMNS,
) -> InfluenceResult:
    if not target:
        return InfluenceResult(notes=["No target column was provided."])
    if "." not in target:
        return InfluenceResult(target=target, notes=["Target must be in table.column format."])
    _validate_limits(max_analysis_rows=max_analysis_rows, max_feature_columns=max_feature_columns)

    table, column = target.split(".", 1)
    if table not in catalog.tables:
        return InfluenceResult(target=target, notes=[f"Target table {table} is not mapped to a CSV."])

    if target == "olist_order_reviews_dataset.review_score":
        frame, notes = _olist_frame(
            con,
            catalog,
            max_analysis_rows=max_analysis_rows,
            max_feature_columns=max_feature_columns,
        )
    else:
        frame, notes = _generic_frame(
            con,
            schema,
            catalog,
            table,
            target_column=column,
            max_analysis_rows=max_analysis_rows,
            max_feature_columns=max_feature_columns,
        )

    if column not in frame.columns:
        return InfluenceResult(target=target, row_count=len(frame), notes=notes + [f"Target column {column} not found."])

    result = InfluenceResult(target=target, row_count=len(frame), notes=notes)
    result.top_features = _score_features(frame, column)[: min(MAX_REPORTED_FEATURES, max_feature_columns)]
    if not result.top_features:
        result.notes.append("No usable feature columns were found for influence analysis.")
    return result


def _generic_frame(
    con: duckdb.DuckDBPyConnection,
    schema: Schema,
    catalog: CsvCatalog,
    table: str,
    target_column: str,
    max_analysis_rows: int,
    max_feature_columns: int,
) -> tuple[pd.DataFrame, list[str]]:
    base = catalog.tables[table]
    if target_column not in base.columns:
        return pd.DataFrame(), _limit_notes(max_analysis_rows, max_feature_columns)

    base_rel = csv_relation(base.csv_path)
    select_parts = [f"t.{quote_ident(target_column)} AS {quote_ident(target_column)}"]
    joins: list[str] = []
    notes = [
        "Generic influence mode: target table plus direct parent FK columns.",
        *_limit_notes(max_analysis_rows, max_feature_columns),
    ]
    selected_features = 0
    candidate_features = 0

    def add_feature(expression: str, feature_name: str) -> None:
        nonlocal candidate_features, selected_features
        if _is_low_value_feature_name(feature_name):
            return
        candidate_features += 1
        if selected_features >= max_feature_columns:
            return
        select_parts.append(f"{expression} AS {quote_ident(feature_name)}")
        selected_features += 1

    for column_name in base.columns:
        if column_name == target_column:
            continue
        add_feature(f"t.{quote_ident(column_name)}", column_name)

    table_schema = schema.tables.get(table)
    if table_schema:
        for column in table_schema.columns.values():
            if not column.foreign_key:
                continue
            parent_table = catalog.tables.get(column.foreign_key.parent_table)
            if not parent_table:
                continue
            alias = f"p_{column.foreign_key.parent_table}"
            parent_rel = csv_relation(parent_table.csv_path)
            child_col = quote_ident(column.name)
            parent_col = quote_ident(column.foreign_key.parent_column)
            joins.append(
                f"LEFT JOIN {parent_rel} {alias} ON t.{child_col} = {alias}.{parent_col}"
            )
            for parent_column in parent_table.columns:
                if parent_column == column.foreign_key.parent_column:
                    continue
                feature_name = f"{column.foreign_key.parent_table}__{parent_column}"
                add_feature(f"{alias}.{quote_ident(parent_column)}", feature_name)

    if candidate_features > selected_features:
        notes.append(
            f"Feature columns truncated from {candidate_features} candidates to "
            f"{selected_features} selected features."
        )

    sql = f"""
    SELECT {", ".join(select_parts)}
    FROM {base_rel} t
    {" ".join(joins)}
    """
    return (
        fetch_bounded_df(
            con,
            sql,
            max_rows=max_analysis_rows,
            max_columns=max_feature_columns + 1,
        ),
        notes,
    )


def _olist_frame(
    con: duckdb.DuckDBPyConnection,
    catalog: CsvCatalog,
    max_analysis_rows: int,
    max_feature_columns: int,
) -> tuple[pd.DataFrame, list[str]]:
    required = [
        "olist_order_reviews_dataset",
        "olist_orders_dataset",
        "olist_customers_dataset",
        "olist_order_payments_dataset",
        "olist_order_items_dataset",
    ]
    missing = [table for table in required if table not in catalog.tables]
    if missing:
        return pd.DataFrame(), [f"Olist preset skipped because tables are missing: {', '.join(missing)}"]

    reviews = csv_relation(catalog.tables["olist_order_reviews_dataset"].csv_path)
    orders = csv_relation(catalog.tables["olist_orders_dataset"].csv_path)
    customers = csv_relation(catalog.tables["olist_customers_dataset"].csv_path)
    payments = csv_relation(catalog.tables["olist_order_payments_dataset"].csv_path)
    items = csv_relation(catalog.tables["olist_order_items_dataset"].csv_path)
    products = _optional_relation(catalog, "olist_products_dataset")
    sellers = _optional_relation(catalog, "olist_sellers_dataset")

    product_join = ""
    product_select = "NULL AS product_category_name,"
    if products:
        product_join = f"LEFT JOIN {products} pr ON i.product_id = pr.product_id"
        product_select = "MIN(pr.product_category_name) AS product_category_name,"

    seller_join = ""
    seller_select = "NULL AS seller_state,"
    if sellers:
        seller_join = f"LEFT JOIN {sellers} se ON i.seller_id = se.seller_id"
        seller_select = "MIN(se.seller_state) AS seller_state,"

    feature_selects = [
        ("order_status", "o.order_status"),
        ("customer_state", "c.customer_state"),
        (
            "delivery_delay_days",
            """
            date_diff(
              'day',
              try_cast(o.order_estimated_delivery_date AS TIMESTAMP),
              try_cast(o.order_delivered_customer_date AS TIMESTAMP)
            )
            """,
        ),
        (
            "delivery_time_days",
            """
            date_diff(
              'day',
              try_cast(o.order_purchase_timestamp AS TIMESTAMP),
              try_cast(o.order_delivered_customer_date AS TIMESTAMP)
            )
            """,
        ),
        ("payment_value_sum", "p.payment_value_sum"),
        ("payment_installments_max", "p.payment_installments_max"),
        ("item_count", "i.item_count"),
        ("price_sum", "i.price_sum"),
        ("freight_value_sum", "i.freight_value_sum"),
        ("product_category_name", "i.product_category_name"),
        ("seller_state", "i.seller_state"),
    ]
    selected_features = feature_selects[:max_feature_columns]
    selected_feature_sql = ",\n      ".join(
        f"{expression} AS {quote_ident(feature_name)}"
        for feature_name, expression in selected_features
    )
    feature_suffix = f",\n      {selected_feature_sql}" if selected_feature_sql else ""
    notes = ["Olist influence preset used for review_score.", *_limit_notes(max_analysis_rows, max_feature_columns)]
    if len(feature_selects) > len(selected_features):
        notes.append(
            f"Feature columns truncated from {len(feature_selects)} candidates to "
            f"{len(selected_features)} selected features."
        )

    sql = f"""
    WITH payment_features AS (
      SELECT
        order_id,
        SUM(try_cast(payment_value AS DOUBLE)) AS payment_value_sum,
        MAX(try_cast(payment_installments AS DOUBLE)) AS payment_installments_max
      FROM {payments}
      GROUP BY order_id
    ),
    item_features AS (
      SELECT
        i.order_id,
        COUNT(*) AS item_count,
        SUM(try_cast(i.price AS DOUBLE)) AS price_sum,
        SUM(try_cast(i.freight_value AS DOUBLE)) AS freight_value_sum,
        {product_select}
        {seller_select}
        1 AS feature_marker
      FROM {items} i
      {product_join}
      {seller_join}
      GROUP BY i.order_id
    )
    SELECT
      try_cast(r.review_score AS DOUBLE) AS review_score
      {feature_suffix}
    FROM {reviews} r
    LEFT JOIN {orders} o ON r.order_id = o.order_id
    LEFT JOIN {customers} c ON o.customer_id = c.customer_id
    LEFT JOIN payment_features p ON r.order_id = p.order_id
    LEFT JOIN item_features i ON r.order_id = i.order_id
    WHERE r.review_score IS NOT NULL
    """
    return (
        fetch_bounded_df(
            con,
            sql,
            max_rows=max_analysis_rows,
            max_columns=max_feature_columns + 1,
        ),
        notes,
    )


def _optional_relation(catalog: CsvCatalog, table: str) -> str | None:
    if table not in catalog.tables:
        return None
    return csv_relation(catalog.tables[table].csv_path)


def _score_features(frame: pd.DataFrame, target_column: str) -> list[InfluenceFeature]:
    if frame.empty:
        return []
    target = pd.to_numeric(frame[target_column], errors="coerce")
    usable = target.notna()
    if usable.sum() < 3:
        return []

    features: list[InfluenceFeature] = []
    for column in frame.columns:
        if column == target_column:
            continue
        if _is_low_value_feature_name(column):
            continue
        series = frame.loc[usable, column]
        target_series = target.loc[usable]
        if series.astype("string").fillna("__NULL__").nunique() <= 1:
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_ratio = numeric.notna().mean() if len(numeric) else 0.0
        if numeric_ratio >= 0.8 and numeric.nunique(dropna=True) > 1:
            features.append(_numeric_score(column, numeric, target_series))
        else:
            categorical = _categorical_score(column, series, target_series)
            if categorical:
                features.append(categorical)

    features = [feature for feature in features if feature.score > 0]
    features.sort(key=lambda item: item.score, reverse=True)
    return features


def _validate_limits(*, max_analysis_rows: int, max_feature_columns: int) -> None:
    if max_analysis_rows <= 0:
        raise ValueError("max_analysis_rows must be greater than zero")
    if max_feature_columns <= 0:
        raise ValueError("max_feature_columns must be greater than zero")


def _limit_notes(max_analysis_rows: int, max_feature_columns: int) -> list[str]:
    return [
        f"Influence dataframe limited to at most {max_analysis_rows} rows.",
        f"Influence dataframe limited to at most {max_feature_columns} feature columns.",
    ]


def _is_low_value_feature_name(column: str) -> bool:
    leaf = column.split("__")[-1].lower()
    if leaf == "id" or leaf.endswith("_id"):
        return True
    if "timestamp" in leaf or leaf.endswith("_date"):
        return True
    return False


def _numeric_score(column: str, series: pd.Series, target: pd.Series) -> InfluenceFeature:
    valid = series.notna() & target.notna()
    if valid.sum() < 3:
        return InfluenceFeature(feature=column, score=0, direction=None, method="pearson", interpretation="")
    pearson = series[valid].corr(target[valid], method="pearson")
    spearman = series[valid].rank().corr(target[valid].rank(), method="pearson")
    candidates = [value for value in [pearson, spearman] if pd.notna(value)]
    score = max((abs(float(value)) for value in candidates), default=0.0)
    direction_value = pearson if pd.notna(pearson) else (spearman if pd.notna(spearman) else 0.0)
    direction = "positive" if direction_value >= 0 else "negative"
    return InfluenceFeature(
        feature=column,
        score=round(score, 6),
        direction=direction,
        method="pearson_spearman",
        interpretation=f"{column} has a {direction} association with the target.",
    )


def _categorical_score(
    column: str,
    series: pd.Series,
    target: pd.Series,
) -> InfluenceFeature | None:
    data = pd.DataFrame({"feature": series.astype("string").fillna("__NULL__").astype(str), "target": target})
    data = data.dropna(subset=["target"])
    if data.empty or data["feature"].nunique() <= 1:
        return None
    top = data["feature"].value_counts().head(30).index
    grouped = data[data["feature"].isin(top)].groupby("feature")["target"].agg(["mean", "count"])
    if grouped.empty or grouped["mean"].nunique() <= 1:
        return None
    target_std = data["target"].std() or 1.0
    effect = float((grouped["mean"].max() - grouped["mean"].min()) / target_std)
    best = grouped["mean"].idxmax()
    worst = grouped["mean"].idxmin()
    return InfluenceFeature(
        feature=column,
        score=round(abs(effect), 6),
        direction="category_effect",
        method="target_mean_by_category",
        interpretation=f"{column} categories vary in target mean; highest={best}, lowest={worst}.",
    )

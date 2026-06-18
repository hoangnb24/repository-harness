from __future__ import annotations

from collections import Counter
from typing import Any

from vsf_profiler.dataset_verdict import SEVERITIES, normalize_severity


ALLOWED_SOURCE_ARTIFACTS = {
    "profile_summary.json",
    "issues.json",
    "relationship_graph.json",
    "dataset_verdict.json",
    "influence.json",
}
STATUS_ORDER = {"invalid": 0, "warning": 1, "skipped": 2, "valid": 3}


def build_chart_specs(
    *,
    profile_summary: dict[str, Any],
    issues: list[dict[str, Any]],
    relationship_graph: dict[str, Any],
    dataset_verdict: dict[str, Any],
    influence: dict[str, Any],
    top_n: int = 10,
) -> dict[str, dict[str, Any]]:
    specs = {
        "issue_counts_by_severity.json": _issue_counts_by_severity_spec(
            dataset_verdict,
            issues,
        ),
        "issue_counts_by_type.json": _issue_counts_by_type_spec(dataset_verdict, issues),
        "missingness_by_table.json": _missingness_by_table_spec(profile_summary),
        "missingness_top_columns.json": _missingness_top_columns_spec(profile_summary, top_n),
        "outliers_top_columns.json": _outliers_top_columns_spec(profile_summary, top_n),
        "relationship_fk_health.json": _relationship_fk_health_spec(relationship_graph),
        "dataset_verdict_risk_summary.json": _dataset_verdict_risk_spec(dataset_verdict),
    }
    influence_spec = _influence_top_features_spec(influence, top_n)
    if influence_spec is not None:
        specs["influence_top_features.json"] = influence_spec
    return dict(sorted(specs.items()))


def _base_spec(
    *,
    chart_id: str,
    title: str,
    chart_type: str,
    source_artifacts: list[str],
    data: list[dict[str, Any]],
    summary: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    unexpected_sources = set(source_artifacts) - ALLOWED_SOURCE_ARTIFACTS
    if unexpected_sources:
        raise ValueError(f"Unsupported chart source artifacts: {sorted(unexpected_sources)}")
    payload: dict[str, Any] = {
        "artifact": "chart_spec",
        "version": 1,
        "chart_id": chart_id,
        "title": title,
        "chart_type": chart_type,
        "source_artifacts": source_artifacts,
        "data": data,
    }
    if summary is not None:
        payload["summary"] = summary
    if details is not None:
        payload["details"] = details
    return payload


def _issue_counts_by_severity_spec(
    dataset_verdict: dict[str, Any],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    issue_counts = dataset_verdict.get("issue_counts") or {}
    by_severity = issue_counts.get("by_severity") or _count_issues_by_severity(issues)
    data = [
        {
            "severity": severity,
            "count": _to_int(by_severity.get(severity)),
            "sort_order": index,
        }
        for index, severity in enumerate(SEVERITIES)
    ]
    return _base_spec(
        chart_id="issue_counts_by_severity",
        title="Issue Counts by Severity",
        chart_type="bar",
        source_artifacts=["dataset_verdict.json", "issues.json"],
        data=data,
        summary={"total": sum(row["count"] for row in data)},
    )


def _issue_counts_by_type_spec(
    dataset_verdict: dict[str, Any],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    issue_counts = dataset_verdict.get("issue_counts") or {}
    by_type = issue_counts.get("by_type") or _count_issues_by_type(issues)
    rows = [
        {"issue_type": issue_type, "count": _to_int(count)}
        for issue_type, count in by_type.items()
    ]
    rows.sort(key=lambda row: (-row["count"], row["issue_type"]))
    return _base_spec(
        chart_id="issue_counts_by_type",
        title="Issue Counts by Type",
        chart_type="bar",
        source_artifacts=["dataset_verdict.json", "issues.json"],
        data=rows,
        summary={"total": sum(row["count"] for row in rows)},
    )


def _missingness_by_table_spec(profile_summary: dict[str, Any]) -> dict[str, Any]:
    rows = _missingness_table_rows(profile_summary)
    return _base_spec(
        chart_id="missingness_by_table",
        title="Missingness by Table",
        chart_type="bar",
        source_artifacts=["profile_summary.json"],
        data=rows,
        summary={"table_count": len(rows)},
    )


def _missingness_top_columns_spec(profile_summary: dict[str, Any], top_n: int) -> dict[str, Any]:
    rows = _missingness_column_rows(profile_summary)
    rows.sort(
        key=lambda row: (
            -row["null_rate"],
            -row["null_count"],
            row["table"],
            row["column"],
        )
    )
    rows = rows[:top_n]
    return _base_spec(
        chart_id="missingness_top_columns",
        title=f"Top {top_n} Columns by Missingness",
        chart_type="horizontal_bar",
        source_artifacts=["profile_summary.json"],
        data=rows,
        summary={"top_n": top_n, "column_count": len(rows)},
    )


def _outliers_top_columns_spec(profile_summary: dict[str, Any], top_n: int) -> dict[str, Any]:
    rows = _outlier_column_rows(profile_summary)
    rows.sort(
        key=lambda row: (
            -row["outlier_count"],
            -row["outlier_rate"],
            row["table"],
            row["column"],
        )
    )
    rows = rows[:top_n]
    return _base_spec(
        chart_id="outliers_top_columns",
        title=f"Top {top_n} Numeric Columns by IQR Outliers",
        chart_type="horizontal_bar",
        source_artifacts=["profile_summary.json"],
        data=rows,
        summary={
            "top_n": top_n,
            "column_count": len(rows),
            "outlier_count": sum(row["outlier_count"] for row in rows),
        },
    )


def _relationship_fk_health_spec(relationship_graph: dict[str, Any]) -> dict[str, Any]:
    summary = relationship_graph.get("summary") or {}
    status_counts = summary.get("status_counts") or {}
    data = [
        {"status": status, "count": _to_int(count), "sort_order": _status_sort_order(status)}
        for status, count in status_counts.items()
    ]
    data.sort(key=lambda row: (row["sort_order"], row["status"]))

    edge_rows = []
    for edge in relationship_graph.get("edges") or []:
        metrics = edge.get("metrics") or {}
        edge_rows.append(
            {
                "id": str(edge.get("id", "")),
                "source_table": str(edge.get("source_table", "")),
                "source_column": str(edge.get("source_column", "")),
                "target_table": str(edge.get("target_table", "")),
                "target_column": str(edge.get("target_column", "")),
                "status": str(edge.get("status", "")),
                "orphan_count": _to_int(metrics.get("orphan_count")),
                "parent_duplicate_count": _to_int(metrics.get("parent_duplicate_count")),
                "child_fk_null_count": _to_int(metrics.get("child_fk_null_count")),
                "join_coverage": _round_float(metrics.get("join_coverage")),
            }
        )
    edge_rows.sort(
        key=lambda row: (
            _status_sort_order(row["status"]),
            -row["orphan_count"],
            -row["parent_duplicate_count"],
            -row["child_fk_null_count"],
            row["id"],
        )
    )
    return _base_spec(
        chart_id="relationship_fk_health",
        title="Relationship FK Health",
        chart_type="status_bar",
        source_artifacts=["relationship_graph.json"],
        data=data,
        summary={
            "node_count": _to_int(summary.get("node_count")),
            "edge_count": _to_int(summary.get("edge_count")),
        },
        details={"edges": edge_rows},
    )


def _dataset_verdict_risk_spec(dataset_verdict: dict[str, Any]) -> dict[str, Any]:
    risk_score = max(0, min(_to_int(dataset_verdict.get("risk_score")), 100))
    remaining_score = 100 - risk_score
    return _base_spec(
        chart_id="dataset_verdict_risk_summary",
        title="EDA Readiness Risk Summary",
        chart_type="gauge",
        source_artifacts=["dataset_verdict.json"],
        data=[
            {"label": "risk", "value": risk_score},
            {"label": "remaining", "value": remaining_score},
        ],
        summary={
            "verdict": dataset_verdict.get("verdict", ""),
            "risk_score": risk_score,
            "issue_count": _to_int((dataset_verdict.get("issue_counts") or {}).get("total")),
        },
    )


def _influence_top_features_spec(
    influence: dict[str, Any],
    top_n: int,
) -> dict[str, Any] | None:
    features = list(influence.get("top_features") or [])
    if not features:
        return None

    rows = [
        {
            "feature": str(feature.get("feature", "")),
            "score": _round_float(feature.get("score")),
            "direction": feature.get("direction") or "",
            "method": str(feature.get("method", "")),
            "interpretation": str(feature.get("interpretation", "")),
        }
        for feature in features
    ]
    rows.sort(key=lambda row: (-abs(row["score"]), row["feature"]))
    rows = [
        {"rank": index, **row}
        for index, row in enumerate(rows[:top_n], start=1)
    ]
    return _base_spec(
        chart_id="influence_top_features",
        title="Influence Top Features",
        chart_type="horizontal_bar",
        source_artifacts=["influence.json"],
        data=rows,
        summary={
            "target": influence.get("target"),
            "method": influence.get("method", ""),
            "row_count": _to_int(influence.get("row_count")),
            "top_n": top_n,
        },
    )


def _count_issues_by_severity(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for issue in issues:
        counts[normalize_severity(issue.get("severity"))] += 1
    return counts


def _count_issues_by_type(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for issue in issues:
        counts[str(issue.get("issue_type", ""))] += 1
    return dict(sorted(counts.items()))


def _missingness_table_rows(profile_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for table_name, table in sorted((profile_summary.get("tables") or {}).items()):
        columns = table.get("columns") or {}
        row_count = _to_int(table.get("row_count"))
        column_count = _to_int(table.get("column_count")) or len(columns)
        null_count = sum(_to_int(column.get("null_count")) for column in columns.values())
        cell_count = row_count * column_count
        rows.append(
            {
                "table": table_name,
                "row_count": row_count,
                "column_count": column_count,
                "null_count": null_count,
                "cell_count": cell_count,
                "null_rate": _safe_rate(null_count, cell_count),
            }
        )
    rows.sort(key=lambda row: (-row["null_rate"], -row["null_count"], row["table"]))
    return rows


def _missingness_column_rows(profile_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for table_name, table in sorted((profile_summary.get("tables") or {}).items()):
        row_count = _to_int(table.get("row_count"))
        for column_name, column in sorted((table.get("columns") or {}).items()):
            null_count = _to_int(column.get("null_count"))
            rows.append(
                {
                    "table": table_name,
                    "column": column_name,
                    "field": f"{table_name}.{column_name}",
                    "row_count": row_count,
                    "null_count": null_count,
                    "null_rate": _round_float(column.get("null_rate")),
                }
            )
    return rows


def _outlier_column_rows(profile_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for table_name, table in sorted((profile_summary.get("tables") or {}).items()):
        row_count = _to_int(table.get("row_count"))
        for column_name, column in sorted((table.get("columns") or {}).items()):
            outliers = column.get("outliers") or {}
            outlier_count = _to_int(outliers.get("outlier_count"))
            if outlier_count <= 0:
                continue
            rows.append(
                {
                    "table": table_name,
                    "column": column_name,
                    "field": f"{table_name}.{column_name}",
                    "method": str(outliers.get("method") or "iqr"),
                    "row_count": row_count,
                    "outlier_count": outlier_count,
                    "outlier_rate": _round_float(outliers.get("outlier_rate")),
                    "q1": _round_nullable_float(outliers.get("q1")),
                    "q3": _round_nullable_float(outliers.get("q3")),
                    "iqr": _round_nullable_float(outliers.get("iqr")),
                    "lower_fence": _round_nullable_float(outliers.get("lower_fence")),
                    "upper_fence": _round_nullable_float(outliers.get("upper_fence")),
                }
            )
    return rows


def _status_sort_order(status: str) -> int:
    return STATUS_ORDER.get(status, 99)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return _round_float(numerator / denominator)


def _round_float(value: Any) -> float:
    try:
        return round(float(value or 0.0), 6)
    except (TypeError, ValueError):
        return 0.0


def _round_nullable_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0

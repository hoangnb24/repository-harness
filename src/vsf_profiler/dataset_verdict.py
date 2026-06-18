from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from vsf_profiler.models import Issue


SEVERITIES = ("P0", "P1", "P2", "P3")
SEVERITY_ORDER = {severity: index for index, severity in enumerate(SEVERITIES)}
SEVERITY_SCALE = {
    "P0": "Run or core dataset contract is blocked.",
    "P1": "Critical data quality or relationship issue likely to break analytics.",
    "P2": "Medium data quality issue that needs cleanup or confirmation.",
    "P3": "Warning, outlier, or review-needed finding.",
}
SEVERITY_ALIASES = {
    "BLOCKER": "P0",
    "CRITICAL": "P0",
    "ERROR": "P1",
    "HIGH": "P1",
    "INFO": "P3",
    "INFORMATIONAL": "P3",
    "LOW": "P3",
    "MEDIUM": "P2",
    "WARNING": "P2",
    "WARN": "P2",
}

ISSUE_RISK_WEIGHTS = {"P0": 30, "P1": 15, "P2": 5, "P3": 1}
RELATIONSHIP_RISK_WEIGHTS = {"invalid": 10, "warning": 4, "skipped": 2}
SCHEMA_RISK_WEIGHTS = {"missing_table_count": 25, "extra_csv_count": 2}


def build_dataset_verdict(
    *,
    issues: list[Issue],
    schema_evaluation: dict[str, Any] | None = None,
    relationship_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issue_rows = [_issue_row(issue) for issue in issues]
    issue_counts = _issue_counts(issue_rows)
    schema_summary = _schema_summary(schema_evaluation)
    relationship_status_counts = _relationship_status_counts(relationship_graph)
    risk_score = _risk_score(issue_counts, schema_summary, relationship_status_counts)
    verdict = _verdict(issue_counts, schema_summary, relationship_status_counts)

    return {
        "artifact": "dataset_verdict",
        "version": 1,
        "verdict": verdict,
        "risk_score": risk_score,
        "verdict_rationale": _verdict_rationale(
            verdict,
            issue_counts,
            schema_summary,
            relationship_status_counts,
        ),
        "severity_scale": SEVERITY_SCALE,
        "issue_counts": issue_counts,
        "schema_summary": schema_summary,
        "relationship_status_counts": relationship_status_counts,
        "top_blockers": _top_blockers(issue_rows),
        "affected_tables": _affected_tables(issue_rows),
        "recommended_next_actions": _recommended_next_actions(
            verdict=verdict,
            issue_rows=issue_rows,
            schema_summary=schema_summary,
            relationship_status_counts=relationship_status_counts,
        ),
    }


def normalize_severity(value: str | None) -> str:
    normalized = str(value or "").strip().upper().replace("-", "_")
    if normalized in SEVERITY_ORDER:
        return normalized
    return SEVERITY_ALIASES.get(normalized, "P3")


def issue_sort_key(issue: Issue) -> tuple[int, int, float, str]:
    severity = normalize_severity(issue.severity)
    return (SEVERITY_ORDER[severity], -issue.bad_count, -issue.bad_rate, issue.issue_id)


def _issue_row(issue: Issue) -> dict[str, Any]:
    severity = normalize_severity(issue.severity)
    return {
        "issue_id": issue.issue_id,
        "issue_type": issue.issue_type,
        "severity": severity,
        "original_severity": issue.severity,
        "table": issue.table,
        "columns": list(issue.columns),
        "parent_table": issue.parent_table,
        "parent_columns": list(issue.parent_columns or []),
        "bad_count": issue.bad_count,
        "total_count": issue.total_count,
        "bad_rate": issue.bad_rate,
        "sample_bad_rows_path": issue.sample_bad_rows_path,
        "suggested_fix": list(issue.suggested_fix),
    }


def _issue_counts(issue_rows: list[dict[str, Any]]) -> dict[str, Any]:
    severity_counts = {severity: 0 for severity in SEVERITIES}
    type_counter: Counter[str] = Counter()
    for row in issue_rows:
        severity_counts[row["severity"]] += 1
        type_counter[row["issue_type"]] += 1
    return {
        "total": len(issue_rows),
        "by_severity": severity_counts,
        "by_type": dict(sorted(type_counter.items())),
    }


def _schema_summary(schema_evaluation: dict[str, Any] | None) -> dict[str, int]:
    summary = (schema_evaluation or {}).get("summary") or {}
    keys = [
        "dbml_table_count",
        "mapped_table_count",
        "missing_table_count",
        "extra_csv_count",
        "schema_issue_count",
    ]
    return {key: _to_int(summary.get(key)) for key in keys}


def _relationship_status_counts(relationship_graph: dict[str, Any] | None) -> dict[str, int]:
    summary = (relationship_graph or {}).get("summary") or {}
    raw_counts = summary.get("status_counts") or {}
    return {str(status): _to_int(count) for status, count in sorted(raw_counts.items())}


def _risk_score(
    issue_counts: dict[str, Any],
    schema_summary: dict[str, int],
    relationship_status_counts: dict[str, int],
) -> int:
    severity_counts = issue_counts["by_severity"]
    score = sum(
        severity_counts[severity] * ISSUE_RISK_WEIGHTS[severity]
        for severity in SEVERITIES
    )
    score += sum(
        relationship_status_counts.get(status, 0) * weight
        for status, weight in RELATIONSHIP_RISK_WEIGHTS.items()
    )
    score += sum(
        schema_summary.get(name, 0) * weight
        for name, weight in SCHEMA_RISK_WEIGHTS.items()
    )
    return min(100, int(score))


def _verdict(
    issue_counts: dict[str, Any],
    schema_summary: dict[str, int],
    relationship_status_counts: dict[str, int],
) -> str:
    severity_counts = issue_counts["by_severity"]
    blocker_issue_count = severity_counts["P0"] + severity_counts["P1"]
    if (
        blocker_issue_count > 0
        or schema_summary.get("missing_table_count", 0) > 0
        or relationship_status_counts.get("invalid", 0) > 0
    ):
        return "NOT_READY"
    if (
        issue_counts["total"] > 0
        or schema_summary.get("extra_csv_count", 0) > 0
        or schema_summary.get("schema_issue_count", 0) > 0
        or relationship_status_counts.get("warning", 0) > 0
        or relationship_status_counts.get("skipped", 0) > 0
    ):
        return "WARN"
    return "READY"


def _verdict_rationale(
    verdict: str,
    issue_counts: dict[str, Any],
    schema_summary: dict[str, int],
    relationship_status_counts: dict[str, int],
) -> str:
    severity_counts = issue_counts["by_severity"]
    if verdict == "NOT_READY":
        parts = []
        blocker_count = severity_counts["P0"] + severity_counts["P1"]
        if blocker_count:
            parts.append(f"{blocker_count} P0/P1 blocker issue(s)")
        if relationship_status_counts.get("invalid", 0):
            parts.append(f"{relationship_status_counts['invalid']} invalid relationship edge(s)")
        if schema_summary.get("missing_table_count", 0):
            parts.append(f"{schema_summary['missing_table_count']} missing DBML table CSV(s)")
        return "; ".join(parts) + " make the dataset not ready for use."
    if verdict == "WARN":
        parts = []
        lower_count = severity_counts["P2"] + severity_counts["P3"]
        if lower_count:
            parts.append(f"{lower_count} P2/P3 issue(s)")
        if relationship_status_counts.get("warning", 0):
            parts.append(f"{relationship_status_counts['warning']} relationship warning(s)")
        if relationship_status_counts.get("skipped", 0):
            parts.append(f"{relationship_status_counts['skipped']} skipped relationship check(s)")
        if schema_summary.get("extra_csv_count", 0):
            parts.append(f"{schema_summary['extra_csv_count']} extra CSV file(s)")
        return "; ".join(parts) + " require review before use."
    return "No blocking or warning findings were detected in the deterministic artifacts."


def _top_blockers(issue_rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        issue_rows,
        key=lambda row: (
            SEVERITY_ORDER[row["severity"]],
            -row["bad_count"],
            -row["bad_rate"],
            row["issue_id"],
        ),
    )
    top_rows = []
    for rank, row in enumerate(sorted_rows[:limit], start=1):
        top_rows.append(
            {
                "rank": rank,
                "issue_id": row["issue_id"],
                "issue_type": row["issue_type"],
                "severity": row["severity"],
                "original_severity": row["original_severity"],
                "table": row["table"],
                "columns": row["columns"],
                "bad_count": row["bad_count"],
                "bad_rate": row["bad_rate"],
                "sample_bad_rows_path": row["sample_bad_rows_path"],
                "suggested_fix": row["suggested_fix"],
            }
        )
    return top_rows


def _affected_tables(issue_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table_groups: dict[str, dict[str, Any]] = defaultdict(_table_group)
    for row in issue_rows:
        table = row["table"] or "dataset"
        group = table_groups[table]
        group["table"] = table
        group["issue_count"] += 1
        group["bad_count"] += row["bad_count"]
        group["issue_counts_by_severity"][row["severity"]] += 1
        group["issue_types"].add(row["issue_type"])
        group["columns"].update(row["columns"])
        if SEVERITY_ORDER[row["severity"]] < SEVERITY_ORDER[group["max_severity"]]:
            group["max_severity"] = row["severity"]

    affected = []
    for group in table_groups.values():
        affected.append(
            {
                "table": group["table"],
                "issue_count": group["issue_count"],
                "max_severity": group["max_severity"],
                "bad_count": group["bad_count"],
                "issue_counts_by_severity": dict(group["issue_counts_by_severity"]),
                "issue_types": sorted(group["issue_types"]),
                "columns": sorted(group["columns"]),
            }
        )
    return sorted(
        affected,
        key=lambda row: (
            SEVERITY_ORDER[row["max_severity"]],
            -row["issue_count"],
            -row["bad_count"],
            row["table"],
        ),
    )


def _table_group() -> dict[str, Any]:
    return {
        "table": "",
        "issue_count": 0,
        "max_severity": "P3",
        "bad_count": 0,
        "issue_counts_by_severity": {severity: 0 for severity in SEVERITIES},
        "issue_types": set(),
        "columns": set(),
    }


def _recommended_next_actions(
    *,
    verdict: str,
    issue_rows: list[dict[str, Any]],
    schema_summary: dict[str, int],
    relationship_status_counts: dict[str, int],
    limit: int = 10,
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()

    if verdict == "NOT_READY":
        _add_action(
            actions,
            seen,
            "Resolve P0/P1 blocker issues before analytics, joins, or model training.",
        )
    if schema_summary.get("missing_table_count", 0):
        _add_action(actions, seen, "Regenerate the extract so every DBML table has a CSV file.")
    if relationship_status_counts.get("invalid", 0):
        _add_action(actions, seen, "Fix invalid foreign-key relationships before cross-table use.")

    for row in sorted(
        issue_rows,
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]],
            -item["bad_count"],
            -item["bad_rate"],
            item["issue_id"],
        ),
    ):
        for action in row["suggested_fix"]:
            _add_action(actions, seen, action)
            if len(actions) >= limit:
                return actions

    if not actions:
        actions.append("No remediation required before use.")
    return actions[:limit]


def _add_action(actions: list[str], seen: set[str], action: str) -> None:
    cleaned = action.strip()
    if cleaned and cleaned not in seen:
        actions.append(cleaned)
        seen.add(cleaned)


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0

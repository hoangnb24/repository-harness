from __future__ import annotations

import re
from collections import Counter
from typing import Any

from vsf_profiler.dataset_verdict import SEVERITIES, SEVERITY_ORDER, normalize_severity
from vsf_profiler.models import Issue, ProfileSummary


ROLE_VALUES = ("fact", "dimension", "bridge", "event", "reference", "unknown")
READINESS_VALUES = ("READY", "WARN", "NOT_READY")
ISSUE_SCORE_WEIGHTS = {"P0": 30, "P1": 18, "P2": 7, "P3": 2}
RELATIONSHIP_SCORE_WEIGHTS = {"invalid": 12, "warning": 6, "skipped": 3}

ROLE_TOKEN_RULES: tuple[tuple[str, set[str]], ...] = (
    ("bridge", {"bridge", "junction", "xref", "crosswalk", "link", "links", "map", "mapping"}),
    ("reference", {"status", "statuses", "type", "types", "code", "codes", "lookup", "reference"}),
    ("event", {"event", "events", "review", "reviews", "feedback", "log", "logs", "audit", "activity", "activities", "session", "sessions", "click", "visit", "history"}),
    ("fact", {"order", "orders", "item", "items", "payment", "payments", "invoice", "invoices", "transaction", "transactions", "sale", "sales", "shipment", "shipments"}),
    ("dimension", {"customer", "customers", "user", "users", "account", "accounts", "product", "products", "seller", "sellers", "vendor", "vendors", "merchant", "merchants"}),
)

BUSINESS_IMPACT_RULES: tuple[dict[str, Any], ...] = (
    {
        "category": "numeric_measure_integrity",
        "label": "Numeric measure integrity",
        "tokens": {"payment", "payments", "invoice", "invoices", "transaction", "transactions", "revenue", "price", "prices", "refund", "refunds", "billing"},
    },
    {
        "category": "feedback_signal_quality",
        "label": "Feedback signal quality",
        "tokens": {"review", "reviews", "rating", "ratings", "feedback", "survey", "surveys"},
    },
    {
        "category": "catalog_attribute_quality",
        "label": "Catalog attribute quality",
        "tokens": {"product", "products", "catalog", "inventory", "sku", "category", "categories"},
    },
    {
        "category": "entity_identity_quality",
        "label": "Entity identity quality",
        "tokens": {"customer", "customers", "user", "users", "account", "accounts", "buyer", "buyers", "client", "clients", "consumer", "consumers"},
    },
    {
        "category": "partner_entity_quality",
        "label": "Partner entity quality",
        "tokens": {"seller", "sellers", "vendor", "vendors", "merchant", "merchants"},
    },
    {
        "category": "transaction_event_quality",
        "label": "Transaction event quality",
        "tokens": {"order", "orders", "shipment", "shipments", "delivery", "deliveries", "item", "items"},
    },
    {
        "category": "reference_data",
        "label": "Reference data",
        "tokens": {"status", "statuses", "type", "types", "code", "codes", "lookup", "reference"},
    },
    {
        "category": "event_analytics",
        "label": "Event analytics",
        "tokens": {"event", "events", "log", "logs", "audit", "activity", "activities", "session", "sessions", "click", "visit", "history"},
    },
    {
        "category": "relationship_integrity",
        "label": "Relationship integrity",
        "tokens": {"bridge", "junction", "xref", "crosswalk", "link", "links", "map", "mapping"},
    },
)

DEFAULT_BUSINESS_IMPACT = {
    "category": "general_analytics",
    "label": "General analytics",
    "tokens": set(),
}
KNOWN_BUSINESS_IMPACT_CATEGORIES = {
    rule["category"] for rule in BUSINESS_IMPACT_RULES
} | {DEFAULT_BUSINESS_IMPACT["category"]}
KNOWN_BUSINESS_IMPACT_LABELS = {
    rule["label"] for rule in BUSINESS_IMPACT_RULES
} | {DEFAULT_BUSINESS_IMPACT["label"]}


def build_table_assessments(
    *,
    profile: ProfileSummary,
    issues: list[Issue],
    relationship_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = relationship_graph or {}
    graph_edges = list(graph.get("edges") or [])
    junction_tables = {
        str(row.get("table"))
        for row in graph.get("junction_tables") or []
        if row.get("table")
    }
    assessments = [
        _table_assessment(
            table_name=table_name,
            table_profile=table_profile.model_dump(mode="json"),
            issues=[issue for issue in issues if issue.table == table_name],
            graph_edges=graph_edges,
            junction_tables=junction_tables,
        )
        for table_name, table_profile in sorted(profile.tables.items())
    ]
    readiness_counts = Counter(row["readiness"] for row in assessments)
    role_counts = Counter(row["role"] for row in assessments)
    impact_counts = Counter(row["business_impact"]["category"] for row in assessments)
    average_score = (
        round(sum(row["health_score"] for row in assessments) / len(assessments), 2)
        if assessments
        else 0
    )
    return {
        "artifact": "table_assessments",
        "version": 1,
        "summary": {
            "table_count": len(assessments),
            "average_health_score": average_score,
            "readiness_counts": {value: readiness_counts.get(value, 0) for value in READINESS_VALUES},
            "role_counts": {value: role_counts.get(value, 0) for value in ROLE_VALUES},
            "business_impact_counts": dict(sorted(impact_counts.items())),
        },
        "assessments": assessments,
    }


def _table_assessment(
    *,
    table_name: str,
    table_profile: dict[str, Any],
    issues: list[Issue],
    graph_edges: list[dict[str, Any]],
    junction_tables: set[str],
) -> dict[str, Any]:
    issue_counts_by_severity = _issue_counts_by_severity(issues)
    issue_counts_by_type = _issue_counts_by_type(issues)
    relationship_risks = _relationship_risks(table_name, graph_edges)
    readiness = _readiness(issue_counts_by_severity, relationship_risks)
    health_score = _health_score(issue_counts_by_severity, relationship_risks)
    affected_columns = sorted(
        {
            column
            for issue in issues
            for column in list(issue.columns) + list(issue.parent_columns or [])
            if column
        }
    )
    role = _infer_role(table_name, graph_edges, junction_tables)
    business_impact = _business_impact(table_name)
    issue_ids = [issue.issue_id for issue in sorted(issues, key=lambda item: item.issue_id)]
    relationship_ids = [risk["relationship_id"] for risk in relationship_risks]
    return {
        "table": table_name,
        "role": role,
        "health_score": health_score,
        "readiness": readiness,
        "row_count": _to_int(table_profile.get("row_count")),
        "column_count": _to_int(table_profile.get("column_count")),
        "issue_counts_by_severity": issue_counts_by_severity,
        "issue_counts_by_type": issue_counts_by_type,
        "affected_columns": affected_columns,
        "relationship_risks": relationship_risks,
        "business_impact": business_impact,
        "evidence_artifacts": _evidence_artifacts(
            table_name=table_name,
            issue_ids=issue_ids,
            relationship_ids=relationship_ids,
        ),
        "recommended_next_actions": _recommended_next_actions(
            table_name=table_name,
            readiness=readiness,
            issues=issues,
            relationship_risks=relationship_risks,
            affected_columns=affected_columns,
        ),
    }


def _issue_counts_by_severity(issues: list[Issue]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for issue in issues:
        counts[normalize_severity(issue.severity)] += 1
    return counts


def _issue_counts_by_type(issues: list[Issue]) -> dict[str, int]:
    counts = Counter(issue.issue_type for issue in issues)
    return dict(sorted(counts.items()))


def _relationship_risks(table_name: str, graph_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    risks = []
    for edge in graph_edges:
        status = str(edge.get("status") or "")
        if status == "valid":
            continue
        source_table = str(edge.get("source_table") or "")
        target_table = str(edge.get("target_table") or "")
        if table_name not in {source_table, target_table}:
            continue
        metrics = edge.get("metrics") if isinstance(edge.get("metrics"), dict) else {}
        risk = {
            "relationship_id": str(edge.get("id") or ""),
            "status": status,
            "status_reason": str(edge.get("status_reason") or ""),
            "role": "child" if source_table == table_name else "parent",
            "source_table": source_table,
            "source_columns": _string_list(edge.get("source_columns") or [edge.get("source_column")]),
            "target_table": target_table,
            "target_columns": _string_list(edge.get("target_columns") or [edge.get("target_column")]),
            "orphan_count": _to_int(metrics.get("orphan_count")),
            "parent_duplicate_count": _to_int(metrics.get("parent_duplicate_count")),
            "child_fk_null_count": _to_int(metrics.get("child_fk_null_count")),
            "join_coverage": _round_float(metrics.get("join_coverage")),
        }
        risks.append(risk)
    return sorted(
        risks,
        key=lambda row: (
            _relationship_status_order(row["status"]),
            -row["orphan_count"],
            -row["parent_duplicate_count"],
            -row["child_fk_null_count"],
            row["relationship_id"],
        ),
    )


def _readiness(issue_counts_by_severity: dict[str, int], relationship_risks: list[dict[str, Any]]) -> str:
    if issue_counts_by_severity["P0"] or issue_counts_by_severity["P1"]:
        return "NOT_READY"
    if any(risk["status"] == "invalid" for risk in relationship_risks):
        return "NOT_READY"
    if issue_counts_by_severity["P2"] or issue_counts_by_severity["P3"]:
        return "WARN"
    if any(risk["status"] in {"warning", "skipped"} for risk in relationship_risks):
        return "WARN"
    return "READY"


def _health_score(issue_counts_by_severity: dict[str, int], relationship_risks: list[dict[str, Any]]) -> int:
    penalty = sum(
        issue_counts_by_severity[severity] * ISSUE_SCORE_WEIGHTS[severity]
        for severity in SEVERITIES
    )
    penalty += sum(
        RELATIONSHIP_SCORE_WEIGHTS.get(risk["status"], 0)
        for risk in relationship_risks
    )
    return max(0, min(100, 100 - penalty))


def _infer_role(
    table_name: str,
    graph_edges: list[dict[str, Any]],
    junction_tables: set[str],
) -> str:
    tokens = _identifier_tokens(table_name)
    if table_name in junction_tables:
        return "bridge"
    for role, role_tokens in ROLE_TOKEN_RULES:
        if tokens & role_tokens:
            return role
    outgoing = sum(1 for edge in graph_edges if edge.get("source_table") == table_name)
    incoming = sum(1 for edge in graph_edges if edge.get("target_table") == table_name)
    if outgoing >= 2 and incoming == 0:
        return "fact"
    if incoming > outgoing:
        return "dimension"
    return "unknown"


def _business_impact(table_name: str) -> dict[str, Any]:
    tokens = _identifier_tokens(table_name)
    for rule in BUSINESS_IMPACT_RULES:
        matched = sorted(tokens & rule["tokens"])
        if not matched:
            continue
        return {
            "category": rule["category"],
            "label": rule["label"],
            "matched_tokens": matched,
            "rationale": f"Inferred from table name token(s): {', '.join(matched)}.",
        }
    return {
        "category": DEFAULT_BUSINESS_IMPACT["category"],
        "label": DEFAULT_BUSINESS_IMPACT["label"],
        "matched_tokens": [],
        "rationale": "No safe analysis-impact token matched the table name.",
    }


def _evidence_artifacts(
    *,
    table_name: str,
    issue_ids: list[str],
    relationship_ids: list[str],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = [
        {
            "artifact": "profile_summary.json",
            "pointer": f"$.tables.{table_name}",
        }
    ]
    if issue_ids:
        refs.append(
            {
                "artifact": "issues.json",
                "issue_ids": issue_ids,
            }
        )
    if relationship_ids:
        refs.append(
            {
                "artifact": "relationship_graph.json",
                "relationship_ids": relationship_ids,
            }
        )
    refs.append(
        {
            "artifact": "table_assessments.json",
            "pointer": f"$.assessments[?(@.table=='{table_name}')]",
        }
    )
    return refs


def _recommended_next_actions(
    *,
    table_name: str,
    readiness: str,
    issues: list[Issue],
    relationship_risks: list[dict[str, Any]],
    affected_columns: list[str],
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    if readiness == "NOT_READY":
        _add_action(actions, seen, f"Resolve blocker issues for `{table_name}` before cross-table analytics.")
    if any(risk["status"] == "invalid" for risk in relationship_risks):
        _add_action(actions, seen, f"Fix invalid relationship checks involving `{table_name}`.")
    if affected_columns:
        _add_action(
            actions,
            seen,
            f"Review affected column(s) in `{table_name}`: {', '.join(affected_columns[:6])}.",
        )
    for issue in sorted(
        issues,
        key=lambda item: (
            SEVERITY_ORDER[normalize_severity(item.severity)],
            -item.bad_count,
            item.issue_id,
        ),
    ):
        for action in issue.suggested_fix:
            _add_action(actions, seen, action)
            if len(actions) >= 6:
                return actions
    if not actions and readiness == "WARN":
        actions.append(f"Review warning-level findings for `{table_name}` before relying on derived metrics.")
    if not actions:
        actions.append(f"No table-level remediation required for `{table_name}`.")
    return actions[:6]


def _add_action(actions: list[str], seen: set[str], action: str) -> None:
    if action and action not in seen:
        actions.append(action)
        seen.add(action)


def _identifier_tokens(identifier: str) -> set[str]:
    parts = re.split(r"[^A-Za-z0-9]+", identifier)
    tokens: set[str] = set()
    for part in parts:
        if not part:
            continue
        lowered = part.lower()
        tokens.add(lowered)
        for subpart in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", part):
            if subpart:
                tokens.add(subpart.lower())
    return tokens


def _relationship_status_order(status: str) -> int:
    return {"invalid": 0, "warning": 1, "skipped": 2, "valid": 3}.get(status, 99)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item)]


def _round_float(value: Any) -> float | None:
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

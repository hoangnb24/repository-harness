from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from vsf_profiler.dataset_verdict import SEVERITIES, issue_sort_key, normalize_severity
from vsf_profiler.models import InfluenceResult, Issue, ProfileSummary


RELATIONSHIP_ISSUES = {
    "ORPHAN_FOREIGN_KEY",
    "PARENT_KEY_DUPLICATE",
    "FOREIGN_KEY_NULL",
    "CHILD_RELATIONSHIP_DUPLICATE",
}


def generate_reports(
    *,
    out_dir: Path,
    profile: ProfileSummary,
    issues: list[Issue],
    influence: InfluenceResult,
    schema_diagram: dict[str, Any],
    schema_parse_report: dict[str, Any] | None = None,
    connector_metadata: dict[str, Any] | None = None,
    lineage_graph: dict[str, Any] | None = None,
    schema_evaluation: dict[str, Any] | None = None,
    relationship_graph: dict[str, Any] | None = None,
    dataset_verdict: dict[str, Any] | None = None,
    table_assessments: dict[str, Any] | None = None,
    chart_specs: dict[str, dict[str, Any]] | None = None,
    run_summary: dict[str, Any] | None = None,
) -> None:
    context = _build_context(
        out_dir,
        profile,
        issues,
        influence,
        schema_diagram,
        schema_parse_report,
        connector_metadata,
        lineage_graph,
        schema_evaluation,
        relationship_graph,
        dataset_verdict,
        table_assessments,
        chart_specs,
        run_summary,
    )
    env = _template_env()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text(env.get_template("report.md.j2").render(**context))
    (out_dir / "report.html").write_text(env.get_template("report.html.j2").render(**context))


def _template_env() -> Environment:
    template_dir = Path(__file__).resolve().parents[2] / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["pct"] = lambda value: f"{float(value) * 100:.2f}%"
    return env


def _build_context(
    out_dir: Path,
    profile: ProfileSummary,
    issues: list[Issue],
    influence: InfluenceResult,
    schema_diagram: dict[str, Any],
    schema_parse_report: dict[str, Any] | None,
    connector_metadata: dict[str, Any] | None,
    lineage_graph: dict[str, Any] | None,
    schema_evaluation: dict[str, Any] | None,
    relationship_graph: dict[str, Any] | None,
    dataset_verdict: dict[str, Any] | None,
    table_assessments: dict[str, Any] | None,
    chart_specs: dict[str, dict[str, Any]] | None,
    run_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    sorted_issues = sorted(issues, key=issue_sort_key)
    verdict_context = _dataset_verdict_context(dataset_verdict)
    schema_parse_context = _schema_parse_report_context(schema_parse_report)
    connector_context = _connector_metadata_context(connector_metadata)
    lineage_context = _lineage_graph_context(lineage_graph)
    schema_context = _schema_evaluation_context(schema_evaluation)
    relationship_context = _relationship_graph_context(relationship_graph)
    table_assessment_context = _table_assessments_context(table_assessments)
    chart_context = _chart_specs_context(chart_specs)
    execution_context = _execution_flow_context(run_summary)
    l4_context = _l4_report_context(run_summary, out_dir)
    table_count = len(profile.tables)
    column_count = sum(table.column_count for table in profile.tables.values())
    row_count = sum(table.row_count for table in profile.tables.values())
    return {
        "summary": {
            "table_count": table_count,
            "column_count": column_count,
            "row_count": row_count,
            "issue_count": len(issues),
            "critical_issue_count": sum(
                1 for issue in issues if normalize_severity(issue.severity) in {"P0", "P1"}
            ),
        },
        "scorecard": _scorecard_context(
            table_count=table_count,
            column_count=column_count,
            row_count=row_count,
            issues=sorted_issues,
            dataset_verdict=verdict_context,
            relationship_graph=relationship_context,
            l4_report=l4_context,
        ),
        "profile": profile,
        "issues": sorted_issues,
        "issue_evidence": _issue_evidence_context(sorted_issues),
        "top_issues": sorted_issues[:15],
        "relationship_issues": [
            issue for issue in sorted_issues if issue.issue_type in RELATIONSHIP_ISSUES
        ],
        "influence": influence,
        "schema_diagram": schema_diagram,
        "schema_parse_report": schema_parse_context,
        "connector_metadata": connector_context,
        "lineage_graph": lineage_context,
        "schema_evaluation": schema_context,
        "relationship_graph": relationship_context,
        "dataset_verdict": verdict_context,
        "table_assessments": table_assessment_context,
        "chart_specs": chart_context,
        "execution_flow": execution_context,
        "l4_report": l4_context,
        "recommended_actions": _recommended_actions(sorted_issues, verdict_context),
    }


def _recommended_actions(issues: list[Issue], dataset_verdict: dict[str, Any]) -> list[str]:
    verdict_actions = dataset_verdict.get("recommended_next_actions", [])
    if verdict_actions:
        return verdict_actions

    actions: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        for action in issue.suggested_fix:
            if action not in seen:
                actions.append(action)
                seen.add(action)
            if len(actions) >= 10:
                return actions
    return actions


def _scorecard_context(
    *,
    table_count: int,
    column_count: int,
    row_count: int,
    issues: list[Issue],
    dataset_verdict: dict[str, Any],
    relationship_graph: dict[str, Any],
    l4_report: dict[str, Any],
) -> list[dict[str, Any]]:
    severity_counts = dataset_verdict.get("severity_counts") or {}
    blocker_count = sum(severity_counts.get(severity, 0) for severity in ("P0", "P1"))
    relationship_counts = relationship_graph.get("status_counts") or {}
    invalid_fk_count = relationship_counts.get("invalid", 0)
    total_fk_count = relationship_graph.get("edge_count", 0)
    l4_status = l4_report.get("status", "not_enabled")
    l4_detail = (
        f"{l4_report.get('provider', 'unknown')} provider"
        if l4_report.get("available")
        else "deterministic run"
    )
    return [
        {
            "label": "Readiness",
            "value": dataset_verdict.get("verdict", "unknown"),
            "detail": "dataset_verdict.json",
            "tone": _tone_for_label(dataset_verdict.get("verdict", "")),
        },
        {
            "label": "Risk",
            "value": f"{dataset_verdict.get('risk_score', 0)}/100",
            "detail": dataset_verdict.get("verdict_rationale", ""),
            "tone": "danger" if _numeric(dataset_verdict.get("risk_score")) >= 75 else "warn",
        },
        {
            "label": "Issues",
            "value": len(issues),
            "detail": f"{blocker_count} P0/P1 blockers",
            "tone": "danger" if blocker_count else "ok",
        },
        {
            "label": "Tables",
            "value": table_count,
            "detail": f"{row_count} rows, {column_count} columns",
            "tone": "info",
        },
        {
            "label": "FK Health",
            "value": f"{invalid_fk_count}/{total_fk_count}",
            "detail": "invalid relationship edges",
            "tone": "danger" if invalid_fk_count else "ok",
        },
        {
            "label": "L4",
            "value": l4_status,
            "detail": l4_detail,
            "tone": _tone_for_l4_status(l4_status),
        },
    ]


def _issue_evidence_context(issues: list[Issue], *, limit: int = 25) -> list[dict[str, Any]]:
    rows = []
    for issue in issues[:limit]:
        parent = ""
        if issue.parent_table:
            parent_columns = ", ".join(issue.parent_columns or [])
            parent = f"{issue.parent_table}.{parent_columns}" if parent_columns else issue.parent_table
        rows.append(
            {
                "issue_id": issue.issue_id,
                "severity": issue.severity,
                "issue_type": issue.issue_type,
                "table": issue.table,
                "columns": issue.columns,
                "columns_text": ", ".join(issue.columns) if issue.columns else "none",
                "parent_ref": parent,
                "bad_count": issue.bad_count,
                "total_count": issue.total_count,
                "bad_rate": issue.bad_rate,
                "sample_bad_rows_path": issue.sample_bad_rows_path or "",
                "probable_cause": "; ".join(issue.probable_causes[:2]) if issue.probable_causes else "",
                "suggested_fix": issue.suggested_fix[0] if issue.suggested_fix else "",
            }
        )
    return rows


def _dataset_verdict_context(dataset_verdict: dict[str, Any] | None) -> dict[str, Any]:
    if not dataset_verdict:
        return {"available": False}

    issue_counts = dataset_verdict.get("issue_counts") or {}
    severity_counts = issue_counts.get("by_severity") or {}
    return {
        "available": True,
        "path": "dataset_verdict.json",
        "verdict": dataset_verdict.get("verdict", ""),
        "risk_score": dataset_verdict.get("risk_score", 0),
        "verdict_rationale": dataset_verdict.get("verdict_rationale", ""),
        "issue_total": issue_counts.get("total", 0),
        "severity_counts": {
            severity: severity_counts.get(severity, 0)
            for severity in SEVERITIES
        },
        "type_counts": issue_counts.get("by_type", {}),
        "schema_summary": dataset_verdict.get("schema_summary") or {},
        "relationship_status_counts": dataset_verdict.get("relationship_status_counts") or {},
        "top_blockers": dataset_verdict.get("top_blockers") or [],
        "affected_tables": dataset_verdict.get("affected_tables") or [],
        "recommended_next_actions": dataset_verdict.get("recommended_next_actions") or [],
    }


def _schema_evaluation_context(schema_evaluation: dict[str, Any] | None) -> dict[str, Any]:
    if not schema_evaluation:
        return {"available": False}
    summary = schema_evaluation.get("summary") or {}
    return {
        "available": True,
        "path": "schema_evaluation.json",
        "mapped_table_count": summary.get("mapped_table_count", 0),
        "missing_table_count": summary.get("missing_table_count", 0),
        "extra_csv_count": summary.get("extra_csv_count", 0),
        "schema_issue_count": summary.get("schema_issue_count", 0),
    }


def _schema_parse_report_context(schema_parse_report: dict[str, Any] | None) -> dict[str, Any]:
    if not schema_parse_report:
        return {"available": False}
    counts = schema_parse_report.get("counts") or {}
    diagnostics = schema_parse_report.get("diagnostics") or []
    unsupported = schema_parse_report.get("unsupported_constructs") or []
    return {
        "available": True,
        "path": "schema_parse_report.json",
        "status": schema_parse_report.get("status", ""),
        "table_count": counts.get("tables", 0),
        "column_count": counts.get("columns", 0),
        "relationship_count": counts.get("relationships", 0),
        "warning_count": counts.get("warnings", 0),
        "unsupported_count": counts.get("unsupported_constructs", 0),
        "diagnostics": diagnostics[:10],
        "unsupported_constructs": unsupported[:10],
    }


def _connector_metadata_context(connector_metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not connector_metadata:
        return {"available": False}
    tables = connector_metadata.get("tables") or []
    return {
        "available": True,
        "path": "connector_metadata.json",
        "source_type": connector_metadata.get("source_type", ""),
        "introspection_status": connector_metadata.get("introspection_status", ""),
        "extraction_status": connector_metadata.get("extraction_status", ""),
        "table_count": len(tables),
        "tables": tables[:10],
        "warning_count": len(connector_metadata.get("warnings") or []),
        "raw_extracts_persisted": connector_metadata.get("raw_extracts_persisted", False),
        "secrets_redacted": connector_metadata.get("secrets_redacted", False),
    }


def _lineage_graph_context(lineage_graph: dict[str, Any] | None) -> dict[str, Any]:
    if not lineage_graph:
        return {"available": False}
    summary = lineage_graph.get("summary") or {}
    evidence_artifacts = lineage_graph.get("evidence_artifacts") or []
    return {
        "available": True,
        "path": "lineage_graph.json",
        "source_system_count": summary.get("source_system_count", 0),
        "schema_count": summary.get("schema_count", 0),
        "table_count": summary.get("table_count", 0),
        "column_count": summary.get("column_count", 0),
        "relationship_count": summary.get("relationship_count", 0),
        "stage_count": summary.get("stage_count", 0),
        "artifact_count": summary.get("artifact_count", 0),
        "edge_count": summary.get("edge_count", 0),
        "connector_source_type": summary.get("connector_source_type", ""),
        "evidence_artifacts": evidence_artifacts[:12],
    }


def _relationship_graph_context(relationship_graph: dict[str, Any] | None) -> dict[str, Any]:
    if not relationship_graph:
        return {"available": False}
    summary = relationship_graph.get("summary") or {}
    status_counts = summary.get("status_counts", {})
    cardinality_counts = summary.get("cardinality_counts", {})
    return {
        "available": True,
        "path": "relationship_graph.json",
        "node_count": summary.get("node_count", 0),
        "edge_count": summary.get("edge_count", 0),
        "status_counts": status_counts,
        "status_counts_text": _format_counts(status_counts),
        "cardinality_counts": cardinality_counts,
        "cardinality_counts_text": _format_counts(cardinality_counts),
        "junction_table_count": summary.get("junction_table_count", 0),
        "many_to_many_relationship_count": summary.get("many_to_many_relationship_count", 0),
        "edges": [
            {
                "id": edge.get("id", ""),
                "status": edge.get("status", ""),
                "declared_cardinality": edge.get("declared_cardinality", edge.get("cardinality", "")),
                "cardinality": edge.get("cardinality", ""),
                "observed_cardinality": edge.get("observed_cardinality", ""),
                "source": _format_endpoint(edge.get("source_table", ""), edge.get("source_columns")),
                "target": _format_endpoint(edge.get("target_table", ""), edge.get("target_columns")),
                "reason": edge.get("status_reason", ""),
            }
            for edge in relationship_graph.get("edges", [])[:10]
        ],
        "junction_tables": relationship_graph.get("junction_tables", [])[:10],
    }


def _table_assessments_context(table_assessments: dict[str, Any] | None) -> dict[str, Any]:
    if not table_assessments:
        return {"available": False, "assessments": []}
    summary = table_assessments.get("summary") or {}
    assessments = []
    for row in table_assessments.get("assessments", [])[:20]:
        impact = row.get("business_impact") or {}
        assessments.append(
            {
                "table": row.get("table", ""),
                "role": row.get("role", ""),
                "health_score": row.get("health_score", 0),
                "readiness": row.get("readiness", ""),
                "issue_total": sum((row.get("issue_counts_by_severity") or {}).values()),
                "affected_columns": row.get("affected_columns") or [],
                "relationship_risk_count": len(row.get("relationship_risks") or []),
                "business_impact_category": impact.get("category", ""),
                "business_impact_label": impact.get("label", ""),
                "business_impact_rationale": impact.get("rationale", ""),
                "analysis_impact_category": impact.get("category", ""),
                "analysis_impact_label": impact.get("label", ""),
                "analysis_impact_rationale": impact.get("rationale", ""),
                "recommended_next_actions": row.get("recommended_next_actions") or [],
            }
        )
    return {
        "available": True,
        "path": "table_assessments.json",
        "table_count": summary.get("table_count", 0),
        "average_health_score": summary.get("average_health_score", 0),
        "readiness_counts": summary.get("readiness_counts") or {},
        "readiness_counts_text": _format_counts(summary.get("readiness_counts") or {}),
        "role_counts": summary.get("role_counts") or {},
        "business_impact_counts": summary.get("business_impact_counts") or {},
        "analysis_impact_counts": summary.get("business_impact_counts") or {},
        "analysis_impact_counts_text": _format_counts(summary.get("business_impact_counts") or {}),
        "assessments": assessments,
    }


def _format_counts(counts: dict[str, Any]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in counts.items())


def _format_endpoint(table: str, columns: Any) -> str:
    if not columns:
        return table
    if len(columns) == 1:
        return f"{table}.{columns[0]}"
    return f"{table}.({', '.join(columns)})"


def _chart_specs_context(chart_specs: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    if not chart_specs:
        return {"available": False, "paths": []}

    return {
        "available": True,
        "paths": [
            {
                "name": spec.get("title", filename),
                "path": f"charts/{filename}",
                "source_artifacts": spec.get("source_artifacts", []),
            }
            for filename, spec in sorted(chart_specs.items())
        ],
        "issue_severity": _chart_data_context(
            chart_specs.get("issue_counts_by_severity.json"),
            value_key="count",
        ),
        "issue_type": _chart_data_context(
            chart_specs.get("issue_counts_by_type.json"),
            value_key="count",
            limit=10,
        ),
        "missingness_tables": _chart_data_context(
            chart_specs.get("missingness_by_table.json"),
            value_key="null_rate",
        ),
        "missingness_columns": _chart_data_context(
            chart_specs.get("missingness_top_columns.json"),
            value_key="null_rate",
        ),
        "relationship_health": _chart_data_context(
            chart_specs.get("relationship_fk_health.json"),
            value_key="count",
        ),
        "relationship_edges": (chart_specs.get("relationship_fk_health.json") or {})
        .get("details", {})
        .get("edges", [])[:10],
        "risk_summary": _risk_chart_context(
            chart_specs.get("dataset_verdict_risk_summary.json"),
        ),
        "influence_top_features": _chart_data_context(
            chart_specs.get("influence_top_features.json"),
            value_key="score",
        ),
    }


def _chart_data_context(
    spec: dict[str, Any] | None,
    *,
    value_key: str,
    limit: int | None = None,
) -> dict[str, Any]:
    if not spec:
        return {"available": False, "title": "", "path": "", "data": [], "summary": {}}
    rows = [dict(row) for row in spec.get("data", [])]
    if limit is not None:
        rows = rows[:limit]
    return {
        "available": True,
        "title": spec.get("title", ""),
        "path": f"charts/{spec.get('chart_id', '')}.json",
        "data": _with_bar_widths(rows, value_key),
        "summary": spec.get("summary", {}),
    }


def _risk_chart_context(spec: dict[str, Any] | None) -> dict[str, Any]:
    if not spec:
        return {"available": False}
    summary = spec.get("summary") or {}
    risk_score = _numeric(summary.get("risk_score"))
    return {
        "available": True,
        "title": spec.get("title", ""),
        "path": "charts/dataset_verdict_risk_summary.json",
        "verdict": summary.get("verdict", ""),
        "risk_score": risk_score,
        "issue_count": summary.get("issue_count", 0),
        "bar_width_pct": max(0.0, min(risk_score, 100.0)),
    }


def _with_bar_widths(rows: list[dict[str, Any]], value_key: str) -> list[dict[str, Any]]:
    max_value = max((_abs_numeric(row.get(value_key)) for row in rows), default=0.0)
    denominator = max(max_value, 1.0)
    enriched = []
    for row in rows:
        enriched_row = dict(row)
        bar_width_pct = round(_abs_numeric(row.get(value_key)) / denominator * 100, 2)
        enriched_row["bar_width_pct"] = bar_width_pct
        enriched_row["bar_text"] = _bar_text(bar_width_pct)
        enriched.append(enriched_row)
    return enriched


def _bar_text(width_pct: float, *, width: int = 20) -> str:
    filled = int(round(max(0.0, min(width_pct, 100.0)) / 100 * width))
    return "#" * filled + "." * (width - filled)


def _tone_for_label(label: str) -> str:
    if label in {"P0", "P1", "NOT_READY", "invalid", "failed"}:
        return "danger"
    if label in {"P2", "WARN", "warning", "fallback_used", "skipped"}:
        return "warn"
    if label in {"P3", "READY", "passed", "success", "completed", "valid"}:
        return "ok"
    return "info"


def _tone_for_l4_status(status: str) -> str:
    if status == "passed":
        return "ok"
    if status == "fallback_used":
        return "warn"
    if status == "failed":
        return "danger"
    return "info"


def _abs_numeric(value: Any) -> float:
    return abs(_numeric(value))


def _numeric(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _execution_flow_context(run_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not run_summary:
        return {"available": False, "stages": [], "artifacts": []}

    stages = []
    for stage in run_summary.get("stage_timings", []):
        stages.append(
            {
                "name": stage.get("display_name") or stage.get("name", ""),
                "status": stage.get("status", ""),
                "duration_seconds": _format_duration(stage.get("duration_seconds")),
                "details": _format_details(stage.get("details") or {}),
                "error": stage.get("error_message") or "",
            }
        )

    artifact_paths = run_summary.get("artifact_paths") or {}
    artifacts = [
        {"name": name, "path": path}
        for name, path in sorted(artifact_paths.items())
        if not name.startswith("sample:")
    ]
    return {
        "available": True,
        "run_id": run_summary.get("run_id", ""),
        "status": run_summary.get("status", ""),
        "duration_seconds": _format_duration(run_summary.get("duration_seconds")),
        "output_dir": run_summary.get("output_dir", ""),
        "stages": stages,
        "artifacts": artifacts,
    }


def _l4_report_context(run_summary: dict[str, Any] | None, out_dir: Path) -> dict[str, Any]:
    if not run_summary:
        return _l4_not_enabled_context()
    artifact_paths = run_summary.get("artifact_paths") or {}
    l4_path = artifact_paths.get("l4_report")
    if not l4_path:
        return _l4_not_enabled_context()
    details = _l4_stage_details(run_summary)
    status = details.get("guardrail_status", "")
    provider = details.get("provider", "")
    fallback_reason = details.get("fallback_reason", "")
    preview_lines = _l4_preview_lines(out_dir / l4_path)
    return {
        "available": True,
        "path": l4_path,
        "guardrail_path": artifact_paths.get("guardrail_report", ""),
        "status": status or "unknown",
        "status_class": status or "unknown",
        "provider": provider or "unknown",
        "model": details.get("model", ""),
        "fallback_reason": fallback_reason,
        "preview_lines": preview_lines,
        "state_text": "Guarded optional L4 EDA narrative available.",
    }


def _l4_not_enabled_context() -> dict[str, Any]:
    return {
        "available": False,
        "path": "",
        "guardrail_path": "",
        "status": "not_enabled",
        "status_class": "not_enabled",
        "provider": "none",
        "model": "",
        "fallback_reason": "",
        "preview_lines": [],
        "state_text": "Optional L4 EDA narrative was not enabled for this deterministic run.",
    }


def _l4_preview_lines(path: Path, *, limit: int = 10) -> list[str]:
    if not path.is_file():
        return []
    lines = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.lstrip("#").strip()
        if line:
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _l4_stage_details(run_summary: dict[str, Any]) -> dict[str, Any]:
    for stage in run_summary.get("stage_timings", []):
        if stage.get("name") == "llm_narrative":
            return stage.get("details") or {}
    return {}


def _format_duration(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value):.3f}"


def _format_details(details: dict[str, Any]) -> str:
    if not details:
        return ""
    parts = []
    for key, value in details.items():
        parts.append(f"{key}={_format_detail_value(value)}")
    return ", ".join(parts)


def _format_detail_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value[:8]) + (", ..." if len(value) > 8 else "") + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key}: {item}" for key, item in list(value.items())[:8]) + "}"
    return str(value)

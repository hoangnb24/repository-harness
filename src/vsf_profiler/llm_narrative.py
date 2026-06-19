from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

from vsf_profiler.table_assessments import (
    KNOWN_BUSINESS_IMPACT_CATEGORIES,
    KNOWN_BUSINESS_IMPACT_LABELS,
)


SOURCE_ARTIFACTS = [
    "profile_summary.json",
    "issues.json",
    "schema_evaluation.json",
    "relationship_graph.json",
    "dataset_verdict.json",
    "table_assessments.json",
    "charts/*.json",
    "influence.json",
]

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
MIN_OPENAI_TIMEOUT_SECONDS = 1.0
MAX_OPENAI_TIMEOUT_SECONDS = 300.0
MIN_OPENAI_MAX_OUTPUT_TOKENS = 64
MAX_OPENAI_MAX_OUTPUT_TOKENS = 8192
MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
SENSITIVE_CONFIG_KEY_PARTS = ("api_key", "authorization", "token", "secret", "password", "credential")

OPENAI_NARRATIVE_INSTRUCTIONS = """You are writing an optional Data Scientist EDA narrative.
Use only the supplied JSON context, which is derived from deterministic structured artifacts.
Do not use external facts, raw CSV data, row-level samples, or unbounded examples.
Do not invent numeric claims; every number must appear in the supplied evidence.
Reference tables, columns, issue ids, issue types, severities, and readiness labels only when they appear in the supplied evidence.
Reference table analysis-impact categories only when they appear in table_assessments.json for that table.
Do not use causal wording such as causes, caused, drives, leads to, due to, because, or root cause.
Use association-only language for influence findings.
The supplied JSON includes guardrail_safe_draft. Return that Markdown exactly.
Do not wrap the response in a code fence. Do not add a preface, suffix, extra bullets, or rewritten wording.
"""

OpenAITransport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]

NUMERIC_CLAIM_RE = re.compile(r"(?<![\w.-])(?P<number>\d+(?:\.\d+)?)(?P<percent>%?)(?![\w.-])")
CODE_REF_RE = re.compile(r"`([^`]+)`")
TABLE_COLUMN_RE = re.compile(r"\b[A-Za-z][\w]*\.[A-Za-z][\w]*\b")
ISSUE_ID_RE = re.compile(r"\bISSUE-\d+\b")
CAUSAL_PATTERNS = {
    "causes": re.compile(r"\bcauses?\b", re.IGNORECASE),
    "caused": re.compile(r"\bcaused\b", re.IGNORECASE),
    "drives": re.compile(r"\bdrives?\b", re.IGNORECASE),
    "driven": re.compile(r"\bdriven\b", re.IGNORECASE),
    "leads_to": re.compile(r"\bleads?\s+to\b", re.IGNORECASE),
    "due_to": re.compile(r"\bdue\s+to\b", re.IGNORECASE),
    "because": re.compile(r"\bbecause\b", re.IGNORECASE),
    "root_cause": re.compile(r"\broot\s+cause\b", re.IGNORECASE),
}
UNSUPPORTED_BUSINESS_IMPACT_TERMS = {
    "customer churn",
    "customer retention",
    "financial reporting",
    "operational efficiency",
    "profitability",
    "revenue growth",
}
ALLOWED_ARTIFACT_FIELD_REFS = {
    "affected_columns",
    "bad_count",
    "business_impact",
    "column_count",
    "health_score",
    "issue_count",
    "issue_counts_by_severity",
    "issue_type",
    "readiness",
    "recommended_next_actions",
    "relationship_risk_count",
    "risk_score",
    "row_count",
    "severity",
    "table_count",
}


class NarrativeProvider(Protocol):
    name: str

    def generate(self, context: dict[str, Any]) -> str:
        """Return a Markdown narrative using only the supplied context."""


@dataclass(frozen=True)
class OpenAIModelConfig:
    model: str = DEFAULT_OPENAI_MODEL
    base_url: str = DEFAULT_OPENAI_BASE_URL
    timeout_seconds: float = 60.0
    max_output_tokens: int = 1200

    def __post_init__(self) -> None:
        object.__setattr__(self, "model", _validated_openai_model(self.model))
        object.__setattr__(self, "base_url", _validated_openai_base_url(self.base_url))
        object.__setattr__(
            self,
            "timeout_seconds",
            _validated_openai_timeout(self.timeout_seconds),
        )
        object.__setattr__(
            self,
            "max_output_tokens",
            _validated_openai_max_output_tokens(self.max_output_tokens),
        )

    def safe_dict(self) -> dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
        }


class FakeNarrativeProvider:
    name = "fake"
    model = "deterministic-fake"

    def config_summary(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "external_api": False,
        }

    def generate(self, context: dict[str, Any]) -> str:
        safe_draft = context.get("guardrail_safe_draft")
        if isinstance(safe_draft, str) and safe_draft.strip():
            return safe_draft
        summary = context["summary"]
        top_issue = next(iter(context["top_issues"]), {})
        top_ref = ""
        if top_issue.get("table") and top_issue.get("columns"):
            top_ref = f"`{top_issue['table']}.{top_issue['columns'][0]}`"
        return (
            "# Data Scientist EDA Narrative\n\n"
            "## EDA Readiness\n\n"
            f"The deterministic artifacts show {summary['table_count']} tables, "
            f"{summary['row_count']} rows, {summary['issue_count']} issues, and a "
            f"risk score of {summary['risk_score']}.\n\n"
            "## Priority Findings\n\n"
            f"The highest-priority reviewed issue type is `{top_issue.get('issue_type', 'none')}` "
            f"on {top_ref or 'the mapped tables'}.\n\n"
            "## Modeling Caveat\n\n"
            "Influence findings are association-only and should be validated before use in decisions.\n"
        )


class OpenAINarrativeProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = DEFAULT_OPENAI_BASE_URL,
        timeout_seconds: float = 60.0,
        max_output_tokens: int = 1200,
        transport: OpenAITransport | None = None,
    ) -> None:
        self.api_key = _validated_openai_api_key(api_key)
        self.config = OpenAIModelConfig(
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )
        self.model = self.config.model
        self.base_url = self.config.base_url
        self.timeout_seconds = self.config.timeout_seconds
        self.max_output_tokens = self.config.max_output_tokens
        self._transport = transport or _default_openai_transport

    def config_summary(self) -> dict[str, Any]:
        return self.config.safe_dict()

    def generate(self, context: dict[str, Any]) -> str:
        payload = {
            "model": self.model,
            "instructions": OPENAI_NARRATIVE_INSTRUCTIONS,
            "input": json.dumps(
                {
                    "task": "Generate the guarded L4 Data Scientist EDA narrative.",
                    "guardrail_safe_draft": context.get("guardrail_safe_draft", ""),
                    "guardrail_contract": context.get("guardrail_contract", {}),
                    "context": context,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            "max_output_tokens": self.max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = self._transport(
            f"{self.base_url}/responses",
            headers,
            payload,
            self.timeout_seconds,
        )
        return _extract_openai_text(response)


def generate_l4_narrative(
    *,
    out_dir: Path,
    artifacts: dict[str, Any],
    provider: NarrativeProvider | None,
) -> dict[str, Any]:
    context = build_narrative_context(artifacts)
    evidence = build_guardrail_evidence(artifacts, context)
    provider_name = getattr(provider, "name", "none") if provider else "none"
    provider_config = _provider_config_summary(provider)
    provider_model = provider_config.get("model", "")
    violations: list[dict[str, Any]] = []
    fallback_reason = ""

    if provider is None:
        fallback_reason = "provider_config_missing"
        narrative = deterministic_l4_narrative(context)
        status = "fallback_used"
        violations.append(
            {
                "type": "provider_config",
                "message": "No LLM provider was configured; deterministic fallback was used.",
            }
        )
    else:
        try:
            candidate = provider.generate(context)
        except Exception as exc:  # pragma: no cover - exact provider failures are adapter-specific.
            fallback_reason = "provider_error"
            candidate = ""
            violations.append(
                {
                    "type": "provider_error",
                    "message": f"{exc.__class__.__name__}: {exc}",
                }
            )
        candidate_guardrail = validate_narrative(candidate, evidence)
        if candidate and candidate_guardrail["status"] == "passed":
            narrative = candidate
            status = "passed"
        else:
            if not fallback_reason:
                fallback_reason = "guardrail_failed"
            violations.extend(candidate_guardrail["violations"])
            narrative = deterministic_l4_narrative(context)
            status = "fallback_used"

    final_guardrail = validate_narrative(narrative, evidence)
    if final_guardrail["status"] != "passed":
        status = "failed"
        violations.extend(final_guardrail["violations"])

    l4_path = out_dir / "l4_report.md"
    guardrail_path = out_dir / "guardrail_report.json"
    l4_path.write_text(narrative, encoding="utf-8")
    guardrail_report = {
        "artifact": "guardrail_report",
        "version": 1,
        "status": status,
        "provider": provider_name,
        "model": provider_model,
        "model_config": provider_config,
        "fallback_reason": fallback_reason,
        "l4_report_path": "l4_report.md",
        "source_artifacts": list(SOURCE_ARTIFACTS),
        "raw_csv_included": False,
        "unbounded_samples_included": False,
        "checked_numbers": final_guardrail["checked_numbers"],
        "checked_refs": final_guardrail["checked_refs"],
        "violation_count": len(violations),
        "violations": violations,
    }
    guardrail_path.write_text(_json_dumps(guardrail_report), encoding="utf-8")
    return {
        "l4_report_path": l4_path,
        "guardrail_report_path": guardrail_path,
        "guardrail_report": guardrail_report,
        "context": context,
    }


def build_narrative_context(artifacts: dict[str, Any]) -> dict[str, Any]:
    profile = artifacts["profile_summary"]
    issues = list(artifacts["issues"])
    dataset_verdict = artifacts["dataset_verdict"]
    schema_evaluation = artifacts["schema_evaluation"]
    relationship_graph = artifacts["relationship_graph"]
    charts = artifacts["chart_specs"]
    influence = artifacts["influence"]
    table_assessments = artifacts.get("table_assessments") or {"assessments": []}
    tables = profile.get("tables") or {}
    issue_counts = dataset_verdict.get("issue_counts") or {}
    context = {
        "role": "Data Scientist",
        "source_artifacts": list(SOURCE_ARTIFACTS),
        "privacy_contract": {
            "raw_csv_included": False,
            "sample_rows_included": False,
            "sample_paths_may_be_referenced": True,
        },
        "summary": {
            "table_count": len(tables),
            "column_count": sum((table.get("column_count") or 0) for table in tables.values()),
            "row_count": sum((table.get("row_count") or 0) for table in tables.values()),
            "issue_count": len(issues),
            "risk_score": dataset_verdict.get("risk_score", 0),
            "verdict": dataset_verdict.get("verdict", ""),
            "severity_counts": issue_counts.get("by_severity") or {},
            "issue_type_counts": issue_counts.get("by_type") or {},
        },
        "tables": [
            {
                "table": table_name,
                "row_count": table.get("row_count", 0),
                "column_count": table.get("column_count", 0),
                "columns": sorted((table.get("columns") or {}).keys()),
            }
            for table_name, table in sorted(tables.items())
        ],
        "top_issues": [
            {
                "issue_id": issue.get("issue_id"),
                "issue_type": issue.get("issue_type"),
                "severity": issue.get("severity"),
                "table": issue.get("table"),
                "columns": issue.get("columns") or [],
                "bad_count": issue.get("bad_count", 0),
                "sample_bad_rows_path": issue.get("sample_bad_rows_path"),
            }
            for issue in issues[:15]
        ],
        "schema_summary": schema_evaluation.get("summary") or {},
        "relationship_summary": relationship_graph.get("summary") or {},
        "dataset_verdict": {
            "verdict": dataset_verdict.get("verdict", ""),
            "verdict_rationale": dataset_verdict.get("verdict_rationale", ""),
            "top_blockers": dataset_verdict.get("top_blockers") or [],
            "recommended_next_actions": dataset_verdict.get("recommended_next_actions") or [],
        },
        "table_assessments": [
            {
                "table": row.get("table"),
                "role": row.get("role"),
                "health_score": row.get("health_score"),
                "readiness": row.get("readiness"),
                "issue_counts_by_severity": row.get("issue_counts_by_severity") or {},
                "affected_columns": row.get("affected_columns") or [],
                "relationship_risk_count": len(row.get("relationship_risks") or []),
                "business_impact": row.get("business_impact") or {},
                "recommended_next_actions": (row.get("recommended_next_actions") or [])[:3],
            }
            for row in (table_assessments.get("assessments") or [])[:10]
        ],
        "chart_summaries": {
            name: spec.get("summary") or {}
            for name, spec in sorted(charts.items())
        },
        "influence": {
            "target": influence.get("target"),
            "method": influence.get("method", ""),
            "row_count": influence.get("row_count", 0),
            "top_features": (influence.get("top_features") or [])[:10],
            "notes": influence.get("notes") or [],
        },
    }
    column_usability_rows = _column_usability_rows(profile, issues)
    context["column_usability_summary"] = _column_usability_summary(column_usability_rows)
    context["column_usability"] = column_usability_rows[:20]
    context["table_health_reviews"] = _table_health_reviews(
        profile,
        context["table_assessments"],
        issues,
    )
    context["column_issue_blocks"] = _column_issue_blocks(issues)
    safe_draft = guardrail_safe_l4_draft(context)
    context["guardrail_safe_draft"] = safe_draft
    context["guardrail_contract"] = _guardrail_contract_from_draft(safe_draft)
    return context


def deterministic_l4_narrative(context: dict[str, Any]) -> str:
    return _structured_l4_narrative(
        context,
        intro="_Deterministic fallback narrative generated from structured artifacts only._",
    )


def guardrail_safe_l4_draft(context: dict[str, Any]) -> str:
    return _structured_l4_narrative(
        context,
        intro="_Guarded provider narrative generated from structured artifacts only._",
    )


def _structured_l4_narrative(context: dict[str, Any], *, intro: str) -> str:
    summary = context["summary"]
    top_issues = context["top_issues"][:5]
    usability_summary = context.get("column_usability_summary") or {}
    lines = [
        "# Data Scientist EDA Narrative",
        "",
        intro,
        "",
        "## EDA Readiness",
        "",
        (
            f"The run reviewed {summary['table_count']} tables, {summary['column_count']} columns, "
            f"and {summary['row_count']} rows. The deterministic readiness label is "
            f"`{summary['verdict']}` with risk score {summary['risk_score']} and "
            f"{summary['issue_count']} issues."
        ),
        "",
        "## Feature Usability Summary",
        "",
        (
            f"The column review classified {usability_summary.get('column_count', 0)} columns: "
            f"{usability_summary.get('ready_count', 0)} ready, "
            f"{usability_summary.get('needs_preparation_count', 0)} needing preparation, and "
            f"{usability_summary.get('blocked_count', 0)} blocked for analysis."
        ),
    ]
    for row in (context.get("column_usability") or [])[:5]:
        lines.append(
            f"- `{row['field']}` is `{row['status_label']}` with severity `{row['severity']}`; "
            f"evidence: {row['evidence']}."
        )
    lines.extend(
        [
            "",
            "## Priority Findings",
            "",
        ]
    )
    if not top_issues:
        lines.append("No issue records were present in `issues.json`.")
    for issue in top_issues:
        columns = issue["columns"]
        ref = f"`{issue['table']}.{columns[0]}`" if columns else f"`{issue['table']}`"
        lines.append(
            f"- `{issue['issue_type']}` on {ref}: {issue['bad_count']} affected rows "
            f"with severity `{issue['severity']}`."
        )
    lines.extend(["", "## Table-by-Table Health Review", ""])
    table_rows = context.get("table_health_reviews") or []
    if not table_rows:
        lines.append("No table assessment rows were present in `table_assessments.json`.")
    for row in table_rows[:5]:
        lines.append(
            f"- `{row['table']}` is `{row['readiness']}` with health score "
            f"{row['health_score']}, role `{row['role']}`, {row['issue_total']} issues, "
            f"and {row['relationship_risk_count']} relationship risks."
        )
    lines.extend(["", "## Column Issue Blocks", ""])
    issue_blocks = context.get("column_issue_blocks") or []
    if not issue_blocks:
        lines.append("No column issue blocks were present in `issues.json`.")
    for block in issue_blocks[:5]:
        lines.append(
            f"- `{block['field']}` has `{block['issue_type']}` with severity "
            f"`{block['severity']}`. Evidence: {block['evidence']}. "
            f"Analysis consequence: {block['analysis_consequence']}"
        )
    relationship_summary = context.get("relationship_summary") or {}
    schema_summary = context.get("schema_summary") or {}
    lines.extend(
        [
            "",
            "## Relationship and Schema Review",
            "",
            (
                f"Relationship evidence includes {relationship_summary.get('edge_count', 0)} edges "
                f"and schema mapping evidence includes {schema_summary.get('mapped_table_count', 0)} mapped tables."
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## Data Quality Next Steps",
            "",
        ]
    )
    actions = context["dataset_verdict"]["recommended_next_actions"][:5]
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- No deterministic next actions were provided.")
    lines.extend(
        [
            "",
            "## Modeling Caveat",
            "",
            (
                "Influence findings are association-only. Validate important patterns with "
                "schema and data owner review before analysis use."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _column_usability_rows(profile: dict[str, Any], issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issue_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for issue in issues:
        table = str(issue.get("table") or "")
        for column in issue.get("columns") or [""]:
            issue_map.setdefault((table, str(column)), []).append(issue)

    rows: list[dict[str, Any]] = []
    for table_name, table in sorted((profile.get("tables") or {}).items()):
        for column_name, column in sorted((table.get("columns") or {}).items()):
            column_issues = issue_map.get((table_name, column_name), [])
            severity = _worst_severity(column_issues)
            outliers = column.get("outliers") or {}
            outlier_count = int(outliers.get("outlier_count") or 0)
            status = _column_status(
                severity=severity,
                null_rate=float(column.get("null_rate") or 0),
                invalid_cast_count=int(column.get("invalid_cast_count") or 0),
                outlier_count=outlier_count,
            )
            rows.append(
                {
                    "field": f"{table_name}.{column_name}",
                    "table": table_name,
                    "column": column_name,
                    "status": status,
                    "status_label": _column_status_label(status),
                    "severity": severity or "none",
                    "issue_count": len(column_issues),
                    "issue_types": sorted({str(issue.get("issue_type") or "") for issue in column_issues}),
                    "null_rate": float(column.get("null_rate") or 0),
                    "invalid_cast_count": int(column.get("invalid_cast_count") or 0),
                    "outlier_count": outlier_count,
                    "evidence": _column_evidence(column, column_issues, outlier_count),
                }
            )
    rows.sort(
        key=lambda row: (
            {"blocked": 0, "needs_preparation": 1, "ready": 2}.get(str(row["status"]), 3),
            _severity_rank(str(row["severity"])),
            -int(row["issue_count"]),
            str(row["field"]),
        )
    )
    return rows


def _column_usability_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "column_count": len(rows),
        "ready_count": sum(1 for row in rows if row.get("status") == "ready"),
        "needs_preparation_count": sum(1 for row in rows if row.get("status") == "needs_preparation"),
        "blocked_count": sum(1 for row in rows if row.get("status") == "blocked"),
    }


def _table_health_reviews(
    profile: dict[str, Any],
    table_assessments: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    issues_by_table: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        issues_by_table.setdefault(str(issue.get("table") or ""), []).append(issue)
    reviews = []
    profile_tables = profile.get("tables") or {}
    for row in table_assessments[:10]:
        table_name = str(row.get("table") or "")
        table_profile = profile_tables.get(table_name) or {}
        table_issues = issues_by_table.get(table_name, [])
        impact = row.get("business_impact") or {}
        reviews.append(
            {
                "table": table_name,
                "role": row.get("role") or "",
                "readiness": row.get("readiness") or "",
                "health_score": row.get("health_score") or 0,
                "row_count": table_profile.get("row_count") or 0,
                "column_count": table_profile.get("column_count") or 0,
                "issue_total": sum((row.get("issue_counts_by_severity") or {}).values()),
                "relationship_risk_count": row.get("relationship_risk_count") or 0,
                "affected_columns": row.get("affected_columns") or [],
                "analysis_impact_category": impact.get("category") or "general_analytics",
                "analysis_impact_label": impact.get("label") or "General analytics",
                "top_issue_types": sorted({str(issue.get("issue_type") or "") for issue in table_issues})[:5],
            }
        )
    return reviews


def _column_issue_blocks(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks = []
    for issue in issues[:30]:
        for column in issue.get("columns") or ["table_level"]:
            table = str(issue.get("table") or "")
            field = table if column == "table_level" else f"{table}.{column}"
            blocks.append(
                {
                    "field": field,
                    "issue_id": issue.get("issue_id") or "",
                    "issue_type": issue.get("issue_type") or "",
                    "severity": issue.get("severity") or "",
                    "evidence": (
                        f"{issue.get('bad_count', 0)}/{issue.get('total_count', 0)} rows; "
                        f"bad rate {float(issue.get('bad_rate') or 0):.6f}"
                    ),
                    "analysis_consequence": _issue_analysis_consequence(str(issue.get("issue_type") or "")),
                }
            )
    blocks.sort(
        key=lambda block: (
            _severity_rank(str(block["severity"])),
            str(block["field"]),
            str(block["issue_id"]),
        )
    )
    return blocks[:20]


def _column_status(
    *,
    severity: str,
    null_rate: float,
    invalid_cast_count: int,
    outlier_count: int,
) -> str:
    if severity in {"P0", "P1"}:
        return "blocked"
    if severity in {"P2", "P3"} or null_rate > 0 or invalid_cast_count > 0 or outlier_count > 0:
        return "needs_preparation"
    return "ready"


def _column_status_label(status: str) -> str:
    return {
        "blocked": "Blocked for analysis",
        "needs_preparation": "Needs preparation",
        "ready": "Ready",
    }.get(status, status)


def _column_evidence(
    column: dict[str, Any],
    issues: list[dict[str, Any]],
    outlier_count: int,
) -> str:
    parts = [
        f"null rate {float(column.get('null_rate') or 0):.6f}",
        f"distinct={int(column.get('distinct_count') or 0)}",
    ]
    invalid_cast_count = int(column.get("invalid_cast_count") or 0)
    if invalid_cast_count:
        parts.append(f"invalid_casts={invalid_cast_count}")
    if outlier_count:
        parts.append(f"iqr_outliers={outlier_count}")
    if issues:
        parts.append(f"issues={len(issues)}")
    return "; ".join(parts)


def _worst_severity(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return ""
    return min((str(issue.get("severity") or "") for issue in issues), key=_severity_rank)


def _severity_rank(severity: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(severity, 4)


def _issue_analysis_consequence(issue_type: str) -> str:
    if issue_type in {"PRIMARY_KEY_NULL", "DUPLICATE_PRIMARY_KEY", "UNIQUE_DUPLICATE"}:
        return "Entity-level joins and splits may be unreliable until key evidence is fixed."
    if issue_type in {"ORPHAN_FOREIGN_KEY", "PARENT_KEY_DUPLICATE", "FOREIGN_KEY_NULL", "CHILD_RELATIONSHIP_DUPLICATE"}:
        return "Cross-table joins may drop, multiply, or misalign records during feature construction."
    if issue_type in {"REQUIRED_FIELD_NULL", "EMPTY_STRING", "INVALID_PLACEHOLDER_TOKEN"}:
        return "Missingness handling is required before aggregate analysis or model feature use."
    if issue_type in {"VALUE_OUT_OF_RANGE", "NEGATIVE_VALUE_NOT_ALLOWED", "NUMERIC_OUTLIER"}:
        return "Distribution-sensitive aggregates and models may need capping, transformation, or exclusion decisions."
    if issue_type in {"TYPE_CAST_INVALID", "DATE_ORDER_INVALID", "REGEX_MISMATCH"}:
        return "Typed, time-based, or pattern-derived features need normalization before analysis use."
    if issue_type in {"TABLE_MISSING", "COLUMN_MISSING", "EXTRA_COLUMN"}:
        return "Schema coverage should be confirmed before comparing tables or training models."
    return "Dataset readiness is reduced until this evidence is reviewed."


def _guardrail_contract_from_draft(draft: str) -> dict[str, Any]:
    number_claims = sorted({match.group(0) for match in NUMERIC_CLAIM_RE.finditer(draft)})
    refs = set(TABLE_COLUMN_RE.findall(draft))
    refs.update(ISSUE_ID_RE.findall(draft))
    for code_ref in CODE_REF_RE.findall(draft):
        cleaned = code_ref.strip()
        if _is_reference_like(cleaned):
            refs.add(cleaned)
    return {
        "required_output": "Return guardrail_safe_draft exactly as Markdown.",
        "allowed_numeric_claims_in_draft": number_claims,
        "allowed_reference_claims_in_draft": sorted(refs),
        "forbidden_causal_terms": sorted(CAUSAL_PATTERNS),
        "style": [
            "No code fences.",
            "No preface or suffix.",
            "No additional numeric claims.",
            "No causal wording.",
            "Use association-only wording for influence findings.",
        ],
    }


def build_guardrail_evidence(
    artifacts: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    numbers: dict[str, set[str]] = {}
    refs: dict[str, set[str]] = {}
    _collect_numbers(context, "$.context", numbers)
    _collect_numbers(artifacts, "$.artifacts", numbers)
    _collect_refs(artifacts, refs)
    _collect_refs(context, refs)
    for artifact in SOURCE_ARTIFACTS:
        refs.setdefault(artifact, set()).add("source_artifacts")
    refs.setdefault("l4_report.md", set()).add("optional_artifact")
    refs.setdefault("guardrail_report.json", set()).add("optional_artifact")
    refs.setdefault("association-only", set()).add("allowed_phrase")
    refs.setdefault("association", set()).add("allowed_phrase")
    refs.setdefault("READY", set()).add("verdict")
    refs.setdefault("WARN", set()).add("verdict")
    refs.setdefault("NOT_READY", set()).add("verdict")
    for field_ref in ALLOWED_ARTIFACT_FIELD_REFS:
        refs.setdefault(field_ref, set()).add("artifact_field")
    numbers.setdefault("100", set()).add("risk_score_scale")
    return {
        "numbers": numbers,
        "refs": refs,
        "business_impacts": _business_impact_evidence(artifacts),
    }


def validate_narrative(markdown: str, evidence: dict[str, Any]) -> dict[str, Any]:
    checked_numbers, number_violations = _check_numbers(markdown, evidence["numbers"])
    checked_refs, ref_violations = _check_refs(markdown, evidence["refs"])
    checked_business_refs, business_violations = _check_business_impact_claims(
        markdown,
        evidence.get("business_impacts") or {},
    )
    causal_violations = _check_causal_wording(markdown)
    violations = number_violations + ref_violations + business_violations + causal_violations
    return {
        "status": "failed" if violations else "passed",
        "checked_numbers": checked_numbers,
        "checked_refs": checked_refs + checked_business_refs,
        "violations": violations,
    }


def _check_numbers(
    markdown: str,
    allowed_numbers: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    checked = []
    violations = []
    for match in NUMERIC_CLAIM_RE.finditer(markdown):
        claim = match.group(0)
        number = match.group("number")
        keys = _number_keys(number, is_percent=bool(match.group("percent")))
        evidence_paths = sorted({path for key in keys for path in allowed_numbers.get(key, set())})
        status = "passed" if evidence_paths else "failed"
        row = {
            "claim": claim,
            "normalized": keys[0],
            "status": status,
            "evidence_paths": evidence_paths,
        }
        checked.append(row)
        if status == "failed":
            violations.append(
                {
                    "type": "numeric_claim",
                    "claim": claim,
                    "message": "Numeric claim is not present in allowed structured evidence.",
                }
            )
    return checked, violations


def _check_refs(
    markdown: str,
    allowed_refs: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims = set(TABLE_COLUMN_RE.findall(markdown))
    claims.update(ISSUE_ID_RE.findall(markdown))
    for code_ref in CODE_REF_RE.findall(markdown):
        cleaned = code_ref.strip()
        if _is_reference_like(cleaned):
            claims.add(cleaned)

    checked = []
    violations = []
    for ref in sorted(claims):
        evidence_paths = sorted(allowed_refs.get(ref, set()))
        status = "passed" if evidence_paths else "failed"
        checked.append(
            {
                "ref": ref,
                "status": status,
                "evidence_paths": evidence_paths,
            }
        )
        if status == "failed":
            violations.append(
                {
                    "type": "reference",
                    "ref": ref,
                    "message": "Reference is not present in allowed structured evidence.",
                }
            )
    return checked, violations


def _check_business_impact_claims(
    markdown: str,
    business_evidence: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_table = business_evidence.get("by_table") or {}
    allowed_terms = set(business_evidence.get("allowed_terms") or [])
    known_terms = set(business_evidence.get("known_terms") or [])
    checked: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    if not known_terms:
        return checked, violations

    for sentence in _sentences(markdown):
        normalized_sentence = _normalize_business_term(sentence)
        matched_terms = [
            term
            for term in sorted(known_terms)
            if _normalize_business_term(term) in normalized_sentence
        ]
        if not matched_terms:
            if _looks_like_business_impact_claim(sentence):
                violations.append(
                    {
                        "type": "business_impact",
                        "claim": sentence.strip(),
                        "message": "Analysis-impact claim does not match table_assessments.json evidence.",
                    }
                )
            continue
        mentioned_tables = [
            table
            for table in by_table
            if re.search(rf"(?<![\w.])`?{re.escape(table)}`?(?![\w.])", sentence)
        ]
        for term in matched_terms:
            normalized_term = _normalize_business_term(term)
            evidence_paths = []
            if normalized_term in allowed_terms:
                evidence_paths.append("table_assessments.json")
            status = "passed" if evidence_paths else "failed"
            checked.append(
                {
                    "ref": term,
                    "status": status,
                    "evidence_paths": evidence_paths,
                }
            )
            if status == "failed":
                violations.append(
                    {
                        "type": "business_impact",
                        "claim": term,
                        "message": "Analysis-impact term is not present in table_assessments.json.",
                    }
                )
                continue
            for table in mentioned_tables:
                table_terms = set(by_table.get(table) or [])
                table_status = "passed" if normalized_term in table_terms else "failed"
                checked.append(
                    {
                        "ref": f"{table}:{term}",
                        "status": table_status,
                        "evidence_paths": ["table_assessments.json"] if table_status == "passed" else [],
                    }
                )
                if table_status == "failed":
                    violations.append(
                        {
                            "type": "table_business_impact",
                            "table": table,
                            "claim": term,
                            "message": "Table-specific analysis-impact claim does not match table_assessments.json.",
                        }
                    )
    return checked, violations


def _check_causal_wording(markdown: str) -> list[dict[str, Any]]:
    violations = []
    for label, pattern in CAUSAL_PATTERNS.items():
        for match in pattern.finditer(markdown):
            violations.append(
                {
                    "type": "causal_wording",
                    "claim": match.group(0),
                    "pattern": label,
                    "message": "Unsupported causal wording is not allowed in L4 narrative.",
                }
            )
    return violations


def _collect_numbers(value: Any, path: str, numbers: dict[str, set[str]]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int | float):
        numbers.setdefault(_normalize_number(value), set()).add(path)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _collect_numbers(item, f"{path}.{key}", numbers)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _collect_numbers(item, f"{path}[{index}]", numbers)


def _collect_refs(value: Any, refs: dict[str, set[str]], path: str = "$") -> None:
    if isinstance(value, dict):
        table_name = value.get("table") or value.get("source_table") or value.get("target_table")
        if isinstance(table_name, str):
            refs.setdefault(table_name, set()).add(path)
            for column in value.get("columns") or value.get("source_columns") or value.get("target_columns") or []:
                if isinstance(column, str):
                    refs.setdefault(column, set()).add(path)
                    refs.setdefault(f"{table_name}.{column}", set()).add(path)
        for key in (
            "issue_id",
            "issue_type",
            "severity",
            "verdict",
            "status",
            "target",
            "feature",
            "role",
            "readiness",
            "category",
            "label",
        ):
            ref = value.get(key)
            if isinstance(ref, str) and ref:
                refs.setdefault(ref, set()).add(f"{path}.{key}")
        for key, item in value.items():
            _collect_refs(item, refs, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _collect_refs(item, refs, f"{path}[{index}]")


def _business_impact_evidence(artifacts: dict[str, Any]) -> dict[str, Any]:
    table_assessments = artifacts.get("table_assessments") or {}
    by_table: dict[str, set[str]] = {}
    allowed_terms: set[str] = set()
    known_terms = set(KNOWN_BUSINESS_IMPACT_CATEGORIES) | set(KNOWN_BUSINESS_IMPACT_LABELS)
    known_terms.update(term.replace("_", " ") for term in KNOWN_BUSINESS_IMPACT_CATEGORIES)
    known_terms.update(UNSUPPORTED_BUSINESS_IMPACT_TERMS)
    for row in table_assessments.get("assessments") or []:
        table = row.get("table")
        impact = row.get("business_impact") or {}
        if not isinstance(table, str) or not table:
            continue
        row_terms = {
            impact.get("category"),
            str(impact.get("category") or "").replace("_", " "),
            impact.get("label"),
        }
        normalized = {
            _normalize_business_term(term)
            for term in row_terms
            if isinstance(term, str) and term
        }
        if normalized:
            by_table[table] = normalized
            allowed_terms.update(normalized)
    return {
        "by_table": {table: sorted(terms) for table, terms in by_table.items()},
        "allowed_terms": sorted(allowed_terms),
        "known_terms": sorted(term for term in known_terms if term),
    }


def _sentences(markdown: str) -> list[str]:
    lines = [line.strip("-# > \t") for line in markdown.splitlines()]
    text = " ".join(line for line in lines if line)
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _looks_like_business_impact_claim(sentence: str) -> bool:
    return bool(
        re.search(
            r"\b(business\s+impact|analysis\s+impact|impact\s+category)\b",
            sentence,
            re.IGNORECASE,
        )
    )


def _normalize_business_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _number_keys(number: str, *, is_percent: bool) -> list[str]:
    value = float(number)
    keys = [_normalize_number(value)]
    if is_percent:
        keys.append(_normalize_number(value / 100))
    return keys


def _normalize_number(value: int | float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def _is_reference_like(value: str) -> bool:
    if not value or value.replace(".", "", 1).isdigit():
        return False
    return bool(re.fullmatch(r"[A-Za-z_][\w.-]*", value))


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _validated_openai_api_key(api_key: str) -> str:
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("OpenAI API key is required when the OpenAI L4 provider is configured.")
    if any(character.isspace() for character in key):
        raise ValueError("OpenAI API key must not contain whitespace.")
    return key


def _validated_openai_model(model: str) -> str:
    model_name = str(model or "").strip()
    if not model_name:
        raise ValueError("VSF_OPENAI_MODEL must not be empty.")
    if not MODEL_NAME_RE.fullmatch(model_name):
        raise ValueError(
            "VSF_OPENAI_MODEL must be 1-128 characters and contain only letters, "
            "numbers, dot, underscore, dash, slash, or colon."
        )
    return model_name


def _validated_openai_base_url(base_url: str) -> str:
    value = str(base_url or "").strip().rstrip("/")
    if not value:
        raise ValueError("VSF_OPENAI_BASE_URL must not be empty.")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("VSF_OPENAI_BASE_URL must be an absolute http(s) URL.")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("VSF_OPENAI_BASE_URL must use HTTPS unless it points to localhost.")
    if parsed.query or parsed.fragment:
        raise ValueError("VSF_OPENAI_BASE_URL must not include query strings or fragments.")
    if any(part == ".." for part in parsed.path.split("/")):
        raise ValueError("VSF_OPENAI_BASE_URL must not contain path traversal segments.")
    return value


def _validated_openai_timeout(timeout_seconds: float) -> float:
    try:
        value = float(timeout_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("VSF_OPENAI_TIMEOUT_SECONDS must be a finite number.") from exc
    if not math.isfinite(value):
        raise ValueError("VSF_OPENAI_TIMEOUT_SECONDS must be a finite number.")
    if value < MIN_OPENAI_TIMEOUT_SECONDS or value > MAX_OPENAI_TIMEOUT_SECONDS:
        raise ValueError(
            "VSF_OPENAI_TIMEOUT_SECONDS must be between "
            f"{MIN_OPENAI_TIMEOUT_SECONDS:g} and {MAX_OPENAI_TIMEOUT_SECONDS:g}."
        )
    return value


def _validated_openai_max_output_tokens(max_output_tokens: int) -> int:
    if isinstance(max_output_tokens, bool):
        raise ValueError("VSF_OPENAI_MAX_OUTPUT_TOKENS must be an integer.")
    try:
        value = int(max_output_tokens)
    except (TypeError, ValueError) as exc:
        raise ValueError("VSF_OPENAI_MAX_OUTPUT_TOKENS must be an integer.") from exc
    if value < MIN_OPENAI_MAX_OUTPUT_TOKENS or value > MAX_OPENAI_MAX_OUTPUT_TOKENS:
        raise ValueError(
            "VSF_OPENAI_MAX_OUTPUT_TOKENS must be between "
            f"{MIN_OPENAI_MAX_OUTPUT_TOKENS} and {MAX_OPENAI_MAX_OUTPUT_TOKENS}."
        )
    return value


def _provider_config_summary(provider: NarrativeProvider | None) -> dict[str, Any]:
    if provider is None:
        return {}
    summary_fn = getattr(provider, "config_summary", None)
    if callable(summary_fn):
        summary = summary_fn()
        if isinstance(summary, dict):
            return _redacted_config_dict(summary)
    provider_name = str(getattr(provider, "name", "unknown"))
    model = getattr(provider, "model", "")
    summary = {"provider": provider_name}
    if model:
        summary["model"] = str(model)
    return summary


def _redacted_config_dict(config: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in config.items():
        key_text = str(key)
        if any(part in key_text.lower() for part in SENSITIVE_CONFIG_KEY_PARTS):
            redacted[key_text] = "[redacted]"
        elif isinstance(value, dict):
            redacted[key_text] = _redacted_config_dict(value)
        elif isinstance(value, list):
            redacted[key_text] = [
                _redacted_config_dict(item) if isinstance(item, dict) else item
                for item in value[:20]
            ]
        else:
            redacted[key_text] = value
    return redacted


def _default_openai_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        message = detail[:500] if detail else exc.reason
        raise RuntimeError(f"OpenAI Responses API failed with HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI Responses API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI Responses API returned invalid JSON.") from exc


def _extract_openai_text(response: dict[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text_parts: list[str] = []
    for output_item in response.get("output") or []:
        if not isinstance(output_item, dict):
            continue
        for content_item in output_item.get("content") or []:
            if not isinstance(content_item, dict):
                continue
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

    if text_parts:
        return "\n".join(text_parts)
    raise RuntimeError("OpenAI Responses API response did not include output text.")

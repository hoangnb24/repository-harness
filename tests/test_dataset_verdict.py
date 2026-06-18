from vsf_profiler.dataset_verdict import build_dataset_verdict, normalize_severity
from vsf_profiler.models import Issue


def test_dataset_verdict_ready_for_clean_artifacts():
    verdict = build_dataset_verdict(
        issues=[],
        schema_evaluation={
            "summary": {
                "dbml_table_count": 2,
                "mapped_table_count": 2,
                "missing_table_count": 0,
                "extra_csv_count": 0,
                "schema_issue_count": 0,
            }
        },
        relationship_graph={"summary": {"status_counts": {"valid": 1}}},
    )

    assert verdict["verdict"] == "READY"
    assert verdict["risk_score"] == 0
    assert verdict["issue_counts"]["total"] == 0
    assert verdict["issue_counts"]["by_severity"] == {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    assert verdict["top_blockers"] == []
    assert verdict["affected_tables"] == []
    assert verdict["recommended_next_actions"] == ["No remediation required before use."]


def test_dataset_verdict_warns_for_low_severity_findings():
    issue = _issue(
        issue_id="ISSUE-0001",
        issue_type="EMPTY_STRING",
        severity="low",
        table="customers",
        columns=["email"],
        bad_count=2,
        suggested_fix=["Convert blank strings to null."],
    )

    verdict = build_dataset_verdict(
        issues=[issue],
        schema_evaluation={"summary": {"schema_issue_count": 0}},
        relationship_graph={"summary": {"status_counts": {"warning": 1}}},
    )

    assert normalize_severity("low") == "P3"
    assert verdict["verdict"] == "WARN"
    assert verdict["risk_score"] == 5
    assert verdict["issue_counts"]["by_severity"]["P3"] == 1
    assert verdict["relationship_status_counts"] == {"warning": 1}
    assert verdict["top_blockers"][0]["severity"] == "P3"
    assert verdict["affected_tables"][0]["table"] == "customers"


def test_dataset_verdict_not_ready_for_blockers_and_invalid_relationships():
    issues = [
        _issue(
            issue_id="ISSUE-0001",
            issue_type="DUPLICATE_PRIMARY_KEY",
            severity="critical",
            table="orders",
            columns=["order_id"],
            bad_count=4,
            suggested_fix=["Deduplicate by primary key."],
        ),
        _issue(
            issue_id="ISSUE-0002",
            issue_type="VALUE_OUT_OF_RANGE",
            severity="WARN",
            table="order_items",
            columns=["price"],
            bad_count=1,
            suggested_fix=["Correct values outside the accepted range."],
        ),
    ]

    verdict = build_dataset_verdict(
        issues=issues,
        schema_evaluation={
            "summary": {
                "dbml_table_count": 3,
                "mapped_table_count": 2,
                "missing_table_count": 1,
                "extra_csv_count": 0,
                "schema_issue_count": 1,
            }
        },
        relationship_graph={"summary": {"status_counts": {"invalid": 1, "valid": 2}}},
    )

    assert normalize_severity("critical") == "P0"
    assert normalize_severity("WARN") == "P2"
    assert verdict["verdict"] == "NOT_READY"
    assert verdict["risk_score"] == 70
    assert verdict["issue_counts"]["by_severity"] == {"P0": 1, "P1": 0, "P2": 1, "P3": 0}
    assert verdict["issue_counts"]["by_type"] == {
        "DUPLICATE_PRIMARY_KEY": 1,
        "VALUE_OUT_OF_RANGE": 1,
    }
    assert verdict["top_blockers"][0]["issue_id"] == "ISSUE-0001"
    assert verdict["top_blockers"][0]["original_severity"] == "critical"
    assert verdict["affected_tables"][0]["table"] == "orders"
    assert verdict["affected_tables"][0]["max_severity"] == "P0"
    assert verdict["recommended_next_actions"][0].startswith("Resolve P0/P1")
    assert "Fix invalid foreign-key relationships" in verdict["recommended_next_actions"][2]


def _issue(
    *,
    issue_id: str,
    issue_type: str,
    severity: str,
    table: str,
    columns: list[str],
    bad_count: int,
    suggested_fix: list[str],
) -> Issue:
    return Issue(
        issue_id=issue_id,
        issue_type=issue_type,
        severity=severity,
        table=table,
        columns=columns,
        bad_count=bad_count,
        total_count=10,
        bad_rate=bad_count / 10,
        evidence_sql="SELECT 1",
        suggested_fix=suggested_fix,
    )

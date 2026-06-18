from vsf_profiler.models import Issue, ProfileSummary, TableProfile
from vsf_profiler.table_assessments import build_table_assessments


def test_table_assessments_score_roles_and_analysis_impact():
    artifact = build_table_assessments(
        profile=ProfileSummary(
            tables={
                "customers": _table("customers"),
                "order_payments": _table("order_payments"),
                "order_reviews": _table("order_reviews"),
            }
        ),
        issues=[
            _issue(
                issue_id="ISSUE-0001",
                issue_type="ORPHAN_FOREIGN_KEY",
                severity="P1",
                table="order_payments",
                columns=["order_id"],
            ),
            _issue(
                issue_id="ISSUE-0002",
                issue_type="REQUIRED_FIELD_NULL",
                severity="P2",
                table="order_reviews",
                columns=["review_score"],
            ),
        ],
        relationship_graph={
            "edges": [
                {
                    "id": "order_payments.order_id->orders.order_id",
                    "source_table": "order_payments",
                    "source_columns": ["order_id"],
                    "target_table": "orders",
                    "target_columns": ["order_id"],
                    "status": "invalid",
                    "status_reason": "child table has orphan foreign keys",
                    "metrics": {
                        "orphan_count": 1,
                        "parent_duplicate_count": 0,
                        "child_fk_null_count": 0,
                        "join_coverage": 0.5,
                    },
                }
            ],
            "junction_tables": [],
        },
    )

    assert artifact["artifact"] == "table_assessments"
    assert artifact["summary"]["table_count"] == 3
    by_table = {row["table"]: row for row in artifact["assessments"]}

    assert by_table["customers"]["readiness"] == "READY"
    assert by_table["customers"]["role"] == "dimension"
    assert by_table["customers"]["business_impact"]["category"] == "entity_identity_quality"

    payments = by_table["order_payments"]
    assert payments["role"] == "fact"
    assert payments["readiness"] == "NOT_READY"
    assert payments["health_score"] < 100
    assert payments["issue_counts_by_severity"]["P1"] == 1
    assert payments["business_impact"]["category"] == "numeric_measure_integrity"
    assert payments["relationship_risks"][0]["relationship_id"] == (
        "order_payments.order_id->orders.order_id"
    )
    assert payments["relationship_risks"][0]["status"] == "invalid"
    assert any(ref["artifact"] == "table_assessments.json" for ref in payments["evidence_artifacts"])

    reviews = by_table["order_reviews"]
    assert reviews["role"] == "event"
    assert reviews["readiness"] == "WARN"
    assert reviews["affected_columns"] == ["review_score"]
    assert reviews["business_impact"]["category"] == "feedback_signal_quality"


def test_bridge_role_uses_existing_junction_detection_metadata():
    artifact = build_table_assessments(
        profile=ProfileSummary(tables={"order_products": _table("order_products")}),
        issues=[],
        relationship_graph={
            "edges": [],
            "junction_tables": [{"table": "order_products", "status": "detected"}],
        },
    )

    assessment = artifact["assessments"][0]
    assert assessment["role"] == "bridge"
    assert assessment["readiness"] == "READY"
    assert assessment["business_impact"]["category"] == "catalog_attribute_quality"


def _table(name: str) -> TableProfile:
    return TableProfile(
        table=name,
        row_count=10,
        column_count=2,
        file_size_mb=0.01,
        columns={},
    )


def _issue(
    *,
    issue_id: str,
    issue_type: str,
    severity: str,
    table: str,
    columns: list[str],
) -> Issue:
    return Issue(
        issue_id=issue_id,
        issue_type=issue_type,
        severity=severity,
        table=table,
        columns=columns,
        bad_count=1,
        total_count=10,
        bad_rate=0.1,
        evidence_sql="SELECT 1",
        suggested_fix=["Review deterministic evidence."],
    )

from vsf_profiler.chart_specs import ALLOWED_SOURCE_ARTIFACTS, build_chart_specs


def test_chart_specs_are_deterministic_and_aggregate_only():
    specs = build_chart_specs(
        profile_summary=_profile_summary(),
        issues=_issues(),
        relationship_graph=_relationship_graph(),
        dataset_verdict=_dataset_verdict(),
        influence=_influence(),
        top_n=2,
    )

    assert list(specs) == [
        "dataset_verdict_risk_summary.json",
        "influence_top_features.json",
        "issue_counts_by_severity.json",
        "issue_counts_by_type.json",
        "missingness_by_table.json",
        "missingness_top_columns.json",
        "relationship_fk_health.json",
    ]
    for spec in specs.values():
        assert spec["artifact"] == "chart_spec"
        assert spec["version"] == 1
        assert set(spec["source_artifacts"]).issubset(ALLOWED_SOURCE_ARTIFACTS)

    severity_rows = specs["issue_counts_by_severity.json"]["data"]
    assert [row["severity"] for row in severity_rows] == ["P0", "P1", "P2", "P3"]
    assert [row["count"] for row in severity_rows] == [1, 2, 0, 1]

    type_rows = specs["issue_counts_by_type.json"]["data"]
    assert type_rows == [
        {"issue_type": "ORPHAN_FOREIGN_KEY", "count": 2},
        {"issue_type": "EMPTY_STRING", "count": 1},
        {"issue_type": "PRIMARY_KEY_NULL", "count": 1},
    ]

    missing_columns = specs["missingness_top_columns.json"]["data"]
    assert [row["field"] for row in missing_columns] == ["orders.customer_id", "customers.email"]
    assert missing_columns[0]["null_rate"] == 0.5
    assert missing_columns[1]["null_rate"] == 0.25

    relationship_rows = specs["relationship_fk_health.json"]["data"]
    assert relationship_rows == [
        {"status": "invalid", "count": 1, "sort_order": 0},
        {"status": "valid", "count": 1, "sort_order": 3},
    ]
    assert specs["relationship_fk_health.json"]["details"]["edges"][0]["id"] == (
        "orders.customer_id->customers.customer_id"
    )

    risk_summary = specs["dataset_verdict_risk_summary.json"]["summary"]
    assert risk_summary == {"verdict": "NOT_READY", "risk_score": 70, "issue_count": 4}
    assert specs["dataset_verdict_risk_summary.json"]["data"] == [
        {"label": "risk", "value": 70},
        {"label": "remaining", "value": 30},
    ]

    influence_rows = specs["influence_top_features.json"]["data"]
    assert [row["feature"] for row in influence_rows] == ["orders__status", "customers__state"]


def test_influence_chart_spec_is_skipped_without_features():
    specs = build_chart_specs(
        profile_summary=_profile_summary(),
        issues=[],
        relationship_graph={"summary": {"status_counts": {}}},
        dataset_verdict={"risk_score": 0, "issue_counts": {"total": 0}},
        influence={"top_features": []},
    )

    assert "influence_top_features.json" not in specs


def _profile_summary() -> dict:
    return {
        "tables": {
            "customers": {
                "row_count": 4,
                "column_count": 2,
                "columns": {
                    "customer_id": {"null_count": 0, "null_rate": 0.0},
                    "email": {"null_count": 1, "null_rate": 0.25},
                },
            },
            "orders": {
                "row_count": 2,
                "column_count": 2,
                "columns": {
                    "order_id": {"null_count": 0, "null_rate": 0.0},
                    "customer_id": {"null_count": 1, "null_rate": 0.5},
                },
            },
        }
    }


def _issues() -> list[dict]:
    return [
        {"issue_type": "ORPHAN_FOREIGN_KEY", "severity": "P1"},
        {"issue_type": "ORPHAN_FOREIGN_KEY", "severity": "P1"},
        {"issue_type": "PRIMARY_KEY_NULL", "severity": "P0"},
        {"issue_type": "EMPTY_STRING", "severity": "P3"},
    ]


def _relationship_graph() -> dict:
    return {
        "summary": {
            "node_count": 2,
            "edge_count": 2,
            "status_counts": {"valid": 1, "invalid": 1},
        },
        "edges": [
            {
                "id": "orders.customer_id->customers.customer_id",
                "source_table": "orders",
                "source_column": "customer_id",
                "target_table": "customers",
                "target_column": "customer_id",
                "status": "invalid",
                "metrics": {
                    "orphan_count": 1,
                    "parent_duplicate_count": 0,
                    "child_fk_null_count": 1,
                    "join_coverage": 0.5,
                },
            },
            {
                "id": "orders.order_id->payments.order_id",
                "source_table": "payments",
                "source_column": "order_id",
                "target_table": "orders",
                "target_column": "order_id",
                "status": "valid",
                "metrics": {
                    "orphan_count": 0,
                    "parent_duplicate_count": 0,
                    "child_fk_null_count": 0,
                    "join_coverage": 1.0,
                },
            },
        ],
    }


def _dataset_verdict() -> dict:
    return {
        "verdict": "NOT_READY",
        "risk_score": 70,
        "issue_counts": {
            "total": 4,
            "by_severity": {"P0": 1, "P1": 2, "P2": 0, "P3": 1},
            "by_type": {
                "EMPTY_STRING": 1,
                "ORPHAN_FOREIGN_KEY": 2,
                "PRIMARY_KEY_NULL": 1,
            },
        },
    }


def _influence() -> dict:
    return {
        "target": "orders.review_score",
        "method": "association_not_causation",
        "row_count": 2,
        "top_features": [
            {"feature": "customers__state", "score": 0.25, "method": "target_mean"},
            {"feature": "orders__status", "score": 0.75, "method": "target_mean"},
        ],
    }

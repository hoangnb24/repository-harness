import json

from vsf_profiler.cli import run_pipeline
from vsf_profiler.demo_data import create_small_demo


def test_yaml_rules_emit_specific_issue_types(tmp_path):
    data_dir = create_small_demo(tmp_path / "demo")
    out_dir = tmp_path / "out"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
    )

    issues = json.loads((out_dir / "issues.json").read_text())
    by_type = {issue["issue_type"]: issue for issue in issues}
    assert by_type["VALUE_OUT_OF_RANGE"]["table"] == "order_reviews"
    assert by_type["NEGATIVE_VALUE_NOT_ALLOWED"]["table"] == "order_payments"
    assert by_type["DATE_ORDER_INVALID"]["table"] == "orders"


def test_numeric_outlier_issue_uses_profiled_iqr_evidence(tmp_path):
    data_dir = tmp_path / "outlier_demo"
    csv_dir = data_dir / "csv"
    csv_dir.mkdir(parents=True)
    (data_dir / "schema.dbml").write_text(
        """Table measurements {
  row_id varchar [pk, not null]
  value double
}
""",
        encoding="utf-8",
    )
    (csv_dir / "measurements.csv").write_text(
        "row_id,value\nr1,10\nr2,10\nr3,10\nr4,10\nr5,100\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=csv_dir,
        rules_path=None,
        target=None,
        out_dir=out_dir,
    )

    profile = json.loads((out_dir / "profile_summary.json").read_text())
    value_profile = profile["tables"]["measurements"]["columns"]["value"]
    assert value_profile["p25"] == 10.0
    assert value_profile["p50"] == 10.0
    assert value_profile["p75"] == 10.0
    assert value_profile["outliers"] == {
        "method": "iqr",
        "q1": 10.0,
        "q3": 10.0,
        "iqr": 0.0,
        "lower_fence": 10.0,
        "upper_fence": 10.0,
        "outlier_count": 1,
        "outlier_rate": 0.2,
    }

    issues = json.loads((out_dir / "issues.json").read_text())
    outlier_issue = next(issue for issue in issues if issue["issue_type"] == "NUMERIC_OUTLIER")
    assert outlier_issue["severity"] == "P3"
    assert outlier_issue["table"] == "measurements"
    assert outlier_issue["columns"] == ["value"]
    assert outlier_issue["bad_count"] == 1
    assert outlier_issue["sample_bad_rows_path"].startswith("samples/")
    assert (out_dir / outlier_issue["sample_bad_rows_path"]).read_text(encoding="utf-8").splitlines()[1] == "r5,100"

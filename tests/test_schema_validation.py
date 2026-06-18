import csv
import json
from pathlib import Path

from vsf_profiler.cli import run_pipeline
from vsf_profiler.demo_data import create_small_demo


def test_missing_column_emits_column_missing(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    (root / "schema.dbml").write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
          customer_name varchar
        }
        """
    )
    _write_csv(csv_dir / "customers.csv", ["customer_id"], [["C001"]])

    out_dir = tmp_path / "out"
    run_pipeline(
        dbml_path=root / "schema.dbml",
        csv_dir=csv_dir,
        rules_path=None,
        target=None,
        out_dir=out_dir,
    )

    issues = _issues(out_dir)
    assert any(issue["issue_type"] == "COLUMN_MISSING" for issue in issues)


def test_extra_column_emits_extra_column(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    (root / "schema.dbml").write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
        }
        """
    )
    _write_csv(csv_dir / "customers.csv", ["customer_id", "extra_col"], [["C001", "x"]])

    out_dir = tmp_path / "out"
    run_pipeline(
        dbml_path=root / "schema.dbml",
        csv_dir=csv_dir,
        rules_path=None,
        target=None,
        out_dir=out_dir,
    )

    issues = _issues(out_dir)
    assert any(issue["issue_type"] == "EXTRA_COLUMN" for issue in issues)


def test_invalid_float_values_emit_type_cast_invalid(tmp_path):
    root = tmp_path / "case"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    (root / "schema.dbml").write_text(
        """
        Table payments {
          payment_id varchar [pk, not null]
          payment_value float
        }
        """
    )
    _write_csv(
        csv_dir / "payments.csv",
        ["payment_id", "payment_value"],
        [["P001", "abc"], ["P002", "unknown"], ["P003", "12,50"], ["P004", "12.50"]],
    )

    out_dir = tmp_path / "out"
    run_pipeline(
        dbml_path=root / "schema.dbml",
        csv_dir=csv_dir,
        rules_path=None,
        target=None,
        out_dir=out_dir,
    )

    issues = _issues(out_dir)
    type_issue = next(issue for issue in issues if issue["issue_type"] == "TYPE_CAST_INVALID")
    assert type_issue["bad_count"] == 3


def test_report_generated_without_target(tmp_path):
    data_dir = create_small_demo(tmp_path / "demo")
    out_dir = tmp_path / "out"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target=None,
        out_dir=out_dir,
    )

    assert (out_dir / "profile_summary.json").exists()
    assert (out_dir / "issues.json").exists()
    assert (out_dir / "schema_diagram.json").exists()
    assert (out_dir / "run_summary.json").exists()
    assert (out_dir / "report.html").exists()
    influence = json.loads((out_dir / "influence.json").read_text())
    summary = json.loads((out_dir / "run_summary.json").read_text())
    report_md = (out_dir / "report.md").read_text()
    assert influence["top_features"] == []
    assert influence["notes"] == ["No target column was provided."]
    assert summary["skipped_stages"][0]["name"] == "influence_analysis"
    assert summary["skipped_stages"][0]["details"]["skip_reason"] == "No target column was provided."
    assert "Execution Flow" in report_md


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _issues(out_dir: Path) -> list[dict]:
    return json.loads((out_dir / "issues.json").read_text())

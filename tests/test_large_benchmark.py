import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from vsf_profiler.large_benchmark import (
    PERFORMANCE_GUARD_REPORT,
    create_large_benchmark_dataset,
    scan_production_materialization_guards,
)


def test_large_benchmark_generator_is_deterministic(tmp_path):
    first = create_large_benchmark_dataset(
        root=tmp_path / "first",
        rows=120,
        tables=7,
        seed=123,
        signal_columns=6,
    )
    second = create_large_benchmark_dataset(
        root=tmp_path / "second",
        rows=120,
        tables=7,
        seed=123,
        signal_columns=6,
    )

    assert first.table_rows == second.table_rows
    assert first.total_rows == second.total_rows
    assert first.table_rows["orders"] == 120
    assert first.table_rows["order_reviews"] == 120
    assert len(first.table_rows) == 7
    assert _sha256(first.dbml_path) == _sha256(second.dbml_path)
    assert _sha256(first.csv_dir / "order_reviews.csv") == _sha256(
        second.csv_dir / "order_reviews.csv"
    )


def test_large_benchmark_generator_validates_table_count(tmp_path):
    with pytest.raises(ValueError, match="tables must be between"):
        create_large_benchmark_dataset(root=tmp_path / "bad", rows=100, tables=3)


def test_benchmark_script_writes_performance_guard_report(tmp_path):
    work_dir = tmp_path / "benchmark"
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    python_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not python_path else f"src{os.pathsep}{python_path}"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_large_dataset.py",
            "--work-dir",
            str(work_dir),
            "--rows",
            "120",
            "--tables",
            "7",
            "--max-analysis-rows",
            "40",
            "--max-feature-columns",
            "3",
            "--force",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report_path = work_dir / "run" / PERFORMANCE_GUARD_REPORT
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "passed"
    assert report["dataset"]["requested_rows"] == 120
    assert report["dataset"]["requested_tables"] == 7
    assert report["dataset"]["total_rows"] > 120
    assert {table["table"] for table in report["dataset"]["tables"]} == {
        "customers",
        "products",
        "sellers",
        "orders",
        "order_reviews",
        "order_payments",
        "order_items",
    }
    assert report["pipeline"]["run_summary_status"] == "success"
    assert report["pipeline"]["run_event_count"] > 0
    assert any(
        stage["name"] == "profile_csv_tables"
        for stage in report["pipeline"]["stage_timings"]
    )
    assert report["memory"]["supported"] is True
    assert report["memory"]["peak_rss_mb"] > 0
    assert report["limits"]["influence_row_count"] <= 40
    assert report["limits"]["influence_top_feature_count"] <= 3
    assert report["limits"]["analysis_row_limit_enforced"] is True
    assert report["limits"]["analysis_feature_limit_enforced"] is True
    assert report["limits"]["analysis_row_limit_reported"] is True
    assert report["limits"]["analysis_feature_limit_reported"] is True
    assert report["limits"]["feature_truncation_reported"] is True
    assert report["limits"]["postgres_chunk_rows_default"] > 0
    assert report["artifacts"]["chart_generation_success"] is True
    assert report["artifacts"]["report_generation_success"] is True
    assert report["artifacts"]["total_size_bytes"] > 0
    assert report["package"]["success"] is True
    assert Path(report["package"]["manifest_path"]).is_file()
    assert Path(report["package"]["zip_path"]).is_file()
    assert report["artifact_audit"]["status"] == "passed"
    assert report["materialization_guards"]["status"] == "passed"
    assert report["violations"] == []


def test_benchmark_materialization_scan_passes_current_source():
    scan = scan_production_materialization_guards()

    assert scan["status"] == "passed"
    assert scan["violations"] == []


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

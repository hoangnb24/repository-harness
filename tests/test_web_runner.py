import csv
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from vsf_profiler.demo_data import create_small_demo
from vsf_profiler.web_runner import (
    LOCAL_WEB_HOST,
    UploadedFile,
    WebRunStore,
    create_web_server,
)


REQUIRED_ARTIFACTS = {
    "profile_summary.json",
    "issues.json",
    "schema_parse_report.json",
    "lineage_graph.json",
    "schema_evaluation.json",
    "relationship_graph.json",
    "dataset_verdict.json",
    "table_assessments.json",
    "run_events.jsonl",
    "run_summary.json",
    "report.html",
}


def wait_for_job(job, *, seconds=20):
    deadline = time.monotonic() + seconds
    while job.status not in {"succeeded", "failed"} and time.monotonic() < deadline:
        time.sleep(0.05)
    return job.status


def test_web_runner_upload_job_writes_canonical_artifacts(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    store = WebRunStore(run_root=tmp_path / "web_runs")

    job = store.start_job(
        dbml=UploadedFile(
            filename="schema.dbml",
            content=(data_dir / "schema.dbml").read_bytes(),
        ),
        csv_files=[
            UploadedFile(filename=path.name, content=path.read_bytes())
            for path in sorted((data_dir / "csv").glob("*.csv"))
        ],
        rules=UploadedFile(
            filename="rules.yaml",
            content=(data_dir / "rules.yaml").read_bytes(),
        ),
        target="order_reviews.review_score",
    )

    wait_for_job(job)

    assert job.status == "succeeded"
    assert (job.out_dir / "profile_summary.json").exists()
    assert (job.out_dir / "issues.json").exists()
    assert (job.out_dir / "schema_parse_report.json").exists()
    assert (job.out_dir / "lineage_graph.json").exists()
    assert (job.out_dir / "schema_evaluation.json").exists()
    assert (job.out_dir / "relationship_graph.json").exists()
    assert (job.out_dir / "dataset_verdict.json").exists()
    assert (job.out_dir / "table_assessments.json").exists()
    assert (job.out_dir / "charts" / "issue_counts_by_type.json").exists()
    assert (job.out_dir / "run_events.jsonl").exists()
    assert (job.out_dir / "run_summary.json").exists()
    assert (job.out_dir / "report.html").exists()

    payload = store.job_payload(job)
    artifact_paths = {artifact["path"] for artifact in payload["artifacts"]}
    assert REQUIRED_ARTIFACTS.issubset(artifact_paths)


def test_web_runner_path_job_writes_canonical_artifacts_without_csv_upload(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    store = WebRunStore(run_root=tmp_path / "web_runs")

    job = store.start_path_job(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
    )

    wait_for_job(job)

    assert job.status == "succeeded"
    assert job.input_mode == "path"
    assert not list(job.input_dir.rglob("*.csv"))
    assert (job.out_dir / "charts" / "issue_counts_by_type.json").exists()

    payload = store.job_payload(job)
    assert payload["input_mode"] == "path"
    artifact_paths = {artifact["path"] for artifact in payload["artifacts"]}
    assert REQUIRED_ARTIFACTS.issubset(artifact_paths)


def test_web_runner_path_job_validates_inputs_before_start(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    store = WebRunStore(run_root=tmp_path / "web_runs")

    with pytest.raises(ValueError, match="DBML path"):
        store.start_path_job(
            dbml_path=data_dir / "missing.dbml",
            csv_dir=data_dir / "csv",
        )

    unsupported_dbml = data_dir / "schema.txt"
    unsupported_dbml.write_text((data_dir / "schema.dbml").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match=".dbml"):
        store.start_path_job(
            dbml_path=unsupported_dbml,
            csv_dir=data_dir / "csv",
        )

    with pytest.raises(ValueError, match="CSV directory"):
        store.start_path_job(
            dbml_path=data_dir / "schema.dbml",
            csv_dir=data_dir / "schema.dbml",
        )

    empty_csv_dir = tmp_path / "empty_csv"
    empty_csv_dir.mkdir()
    with pytest.raises(ValueError, match="at least one .csv"):
        store.start_path_job(
            dbml_path=data_dir / "schema.dbml",
            csv_dir=empty_csv_dir,
        )

    unsupported_rules = data_dir / "rules.txt"
    unsupported_rules.write_text((data_dir / "rules.yaml").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match=".yaml"):
        store.start_path_job(
            dbml_path=data_dir / "schema.dbml",
            csv_dir=data_dir / "csv",
            rules_path=unsupported_rules,
        )

    with pytest.raises(ValueError, match="table.column"):
        store.start_path_job(
            dbml_path=data_dir / "schema.dbml",
            csv_dir=data_dir / "csv",
            target="review_score",
        )


def test_web_runner_path_job_http_endpoint(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    server = create_web_server(port=0, run_root=tmp_path / "web_runs")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{LOCAL_WEB_HOST}:{server.server_address[1]}"
    try:
        payload = _post_json(
            f"{base_url}/api/path-jobs",
            {
                "dbml_path": str(data_dir / "schema.dbml"),
                "csv_dir": str(data_dir / "csv"),
                "rules_path": str(data_dir / "rules.yaml"),
                "target": "order_reviews.review_score",
            },
        )

        assert payload["status"] in {"queued", "running"}
        assert payload["input_mode"] == "path"

        job_payload = _wait_for_http_job(base_url, payload["job_id"])
        assert job_payload["status"] == "succeeded"
        assert job_payload["input_mode"] == "path"
        artifact_paths = {artifact["path"] for artifact in job_payload["artifacts"]}
        assert REQUIRED_ARTIFACTS.issubset(artifact_paths)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_json(
                f"{base_url}/api/path-jobs",
                {
                    "dbml_path": str(data_dir / "missing.dbml"),
                    "csv_dir": str(data_dir / "csv"),
                },
            )
        assert exc_info.value.code == 400
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_web_runner_dashboard_endpoint_lists_generated_artifact_urls(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    server = create_web_server(port=0, run_root=tmp_path / "web_runs")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{LOCAL_WEB_HOST}:{server.server_address[1]}"
    try:
        payload = _post_json(
            f"{base_url}/api/path-jobs",
            {
                "dbml_path": str(data_dir / "schema.dbml"),
                "csv_dir": str(data_dir / "csv"),
                "rules_path": str(data_dir / "rules.yaml"),
                "target": "order_reviews.review_score",
            },
        )
        job_payload = _wait_for_http_job(base_url, payload["job_id"])
        assert job_payload["status"] == "succeeded"

        dashboard = _get_json(f"{base_url}/api/jobs/{payload['job_id']}/dashboard")
        assert dashboard["job_id"] == payload["job_id"]
        assert dashboard["status"] == "succeeded"
        assert dashboard["missing_artifacts"] == []
        assert "charts/issue_counts_by_severity.json" in dashboard["chart_artifacts"]
        assert "charts/influence_top_features.json" in dashboard["chart_artifacts"]
        assert "charts/outliers_top_columns.json" in dashboard["chart_artifacts"]
        for artifact_path in [
            "issues.json",
            "profile_summary.json",
            "relationship_graph.json",
            "dataset_verdict.json",
            "table_assessments.json",
            "schema_evaluation.json",
            "schema_parse_report.json",
            "lineage_graph.json",
            "influence.json",
            "run_summary.json",
            "charts/issue_counts_by_type.json",
            "charts/outliers_top_columns.json",
        ]:
            assert dashboard["artifact_urls"][artifact_path] == (
                f"/api/jobs/{payload['job_id']}/artifacts/{artifact_path}"
            )

        issue_type_spec = _get_json(
            f"{base_url}{dashboard['artifact_urls']['charts/issue_counts_by_type.json']}"
        )
        assert issue_type_spec["artifact"] == "chart_spec"
        assert issue_type_spec["data"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_web_runner_dashboard_lists_optional_connector_metadata_when_present(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    store = WebRunStore(run_root=tmp_path / "web_runs")
    job = store.start_path_job(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
    )
    wait_for_job(job)
    assert job.status == "succeeded"

    (job.out_dir / "connector_metadata.json").write_text(
        json.dumps(
            {
                "artifact": "connector_metadata",
                "source_type": "postgres",
                "connection": {"url": "[redacted]"},
            }
        ),
        encoding="utf-8",
    )

    payload = store.job_payload(job)
    artifact_paths = {artifact["path"] for artifact in payload["artifacts"]}
    assert "connector_metadata.json" in artifact_paths
    dashboard = store.dashboard_payload(job)
    assert dashboard["artifact_urls"]["connector_metadata.json"] == (
        f"/api/jobs/{job.job_id}/artifacts/connector_metadata.json"
    )


def test_web_runner_dashboard_lists_optional_l4_artifacts_when_present(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    store = WebRunStore(run_root=tmp_path / "web_runs")
    job = store.start_path_job(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
    )
    wait_for_job(job)
    assert job.status == "succeeded"

    (job.out_dir / "l4_report.md").write_text("# Data Scientist EDA Narrative\n", encoding="utf-8")
    (job.out_dir / "guardrail_report.json").write_text(
        json.dumps(
            {
                "artifact": "guardrail_report",
                "status": "passed",
                "provider": "fake",
                "checked_numbers": [],
                "checked_refs": [],
                "violations": [],
            }
        ),
        encoding="utf-8",
    )

    dashboard = store.dashboard_payload(job)
    assert dashboard["artifact_urls"]["l4_report.md"] == (
        f"/api/jobs/{job.job_id}/artifacts/l4_report.md"
    )
    assert dashboard["artifact_urls"]["guardrail_report.json"] == (
        f"/api/jobs/{job.job_id}/artifacts/guardrail_report.json"
    )
    assert "l4_report.md" not in dashboard["required_artifacts"]
    assert "guardrail_report.json" not in dashboard["required_artifacts"]


def test_web_runner_upload_job_applies_mapping_overrides_after_filename_sanitization(tmp_path):
    store = WebRunStore(run_root=tmp_path / "web_runs")

    job = store.start_job(
        dbml=UploadedFile(
            filename="schema.dbml",
            content=b"""
            Table customers {
              customer_id varchar [pk, not null]
              email varchar
            }
            """,
        ),
        csv_files=[
            UploadedFile(
                filename="crm customers.csv",
                content=b"customer_id,email\nC001,a@example.com\n",
            )
        ],
        mapping_overrides={"customers": "crm customers.csv"},
    )

    wait_for_job(job)

    assert job.status == "succeeded"
    schema_evaluation = json.loads((job.out_dir / "schema_evaluation.json").read_text())
    customers = schema_evaluation["tables"][0]
    assert customers["mapping_method"] == "manual"
    assert customers["selected_csv"] == "crm_customers.csv"
    assert customers["matched_columns"] == ["customer_id", "email"]


def test_web_runner_path_job_applies_mapping_overrides(tmp_path):
    root = tmp_path / "data"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    schema_path.write_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
          email varchar
        }
        """,
        encoding="utf-8",
    )
    _write_csv(csv_dir / "crm_customers.csv", ["customer_id", "email"], [["C001", "a@example.com"]])
    store = WebRunStore(run_root=tmp_path / "web_runs")

    job = store.start_path_job(
        dbml_path=schema_path,
        csv_dir=csv_dir,
        mapping_overrides={"customers": "crm_customers.csv"},
    )

    wait_for_job(job)

    assert job.status == "succeeded"
    path_inputs = json.loads((job.input_dir / "path_inputs.json").read_text())
    assert path_inputs["mapping_overrides"] == {"customers": "crm_customers.csv"}
    schema_evaluation = json.loads((job.out_dir / "schema_evaluation.json").read_text())
    assert schema_evaluation["tables"][0]["mapping_method"] == "manual"


def test_web_runner_rejects_artifact_path_traversal(tmp_path):
    store = WebRunStore(run_root=tmp_path / "web_runs")
    job = store.start_job(
        dbml=UploadedFile(filename="schema.dbml", content=b"Table orders { order_id varchar [pk] }"),
        csv_files=[UploadedFile(filename="orders.csv", content=b"order_id\n1\n")],
    )
    wait_for_job(job, seconds=10)

    try:
        store.resolve_artifact(job, "../input/schema.dbml")
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("path traversal was not rejected")


def test_web_server_binds_localhost_only(tmp_path):
    server = create_web_server(port=0, run_root=tmp_path / "web_runs")
    try:
        assert server.server_address[0] == LOCAL_WEB_HOST
    finally:
        server.server_close()


def _post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 202
        return json.loads(response.read().decode("utf-8"))


def _get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_http_job(base_url, job_id):
    deadline = time.monotonic() + 20
    payload = {}
    while time.monotonic() < deadline:
        payload = _get_json(f"{base_url}/api/jobs/{job_id}")
        if payload["status"] in {"succeeded", "failed"}:
            return payload
        time.sleep(0.05)
    return payload


def _write_csv(path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)

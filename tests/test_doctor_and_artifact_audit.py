import json
import os
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from vsf_profiler.artifact_audit import audit_artifacts
from vsf_profiler.cli import app, run_pipeline
from vsf_profiler.demo_data import create_small_demo
from vsf_profiler.export_package import create_analysis_package


def test_doctor_command_redacts_secret_environment_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-value-123456789")
    monkeypatch.setenv(
        "VSF_PROFILER_POSTGRES_URL",
        "postgresql://user:super-secret@127.0.0.1:55432/db?token=query-secret",
    )
    monkeypatch.setenv(
        "VSF_PROFILER_MYSQL_URL",
        "mysql://user:mysql-secret@127.0.0.1:3306/db?token=mysql-token",
    )
    monkeypatch.setenv("VSF_PROFILER_LLM_PROVIDER", "openai")

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "VSF Data Profiler doctor" in result.output
    assert "OPENAI_API_KEY present (redacted)" in result.output
    assert "VSF_PROFILER_POSTGRES_URL present (redacted)" in result.output
    assert "VSF_PROFILER_MYSQL_URL present (redacted)" in result.output
    assert "pdf export backend" in result.output
    for leaked_value in [
        "sk-test-secret-value-123456789",
        "super-secret",
        "query-secret",
        "mysql-secret",
        "mysql-token",
        "postgresql://user:super-secret@127.0.0.1:55432/db",
        "mysql://user:mysql-secret@127.0.0.1:3306/db",
    ]:
        assert leaked_value not in result.output


def test_doctor_reads_openai_config_from_dotenv_without_leaking_values(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("VSF_PROFILER_LLM_PROVIDER", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "VSF_PROFILER_LLM_PROVIDER=openai",
                "OPENAI_API_KEY=sk-dotenv-secret-value-123456789",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "OPENAI_API_KEY present (redacted)" in result.output
    assert "VSF_PROFILER_LLM_PROVIDER present" in result.output
    assert "sk-dotenv-secret-value-123456789" not in result.output


def test_artifact_audit_passes_for_demo_run_package_and_zip(tmp_path):
    out_dir = _demo_output(tmp_path)
    package_dir = tmp_path / "analysis_package"
    package_result = create_analysis_package(
        input_dir=out_dir,
        output_dir=package_dir,
        create_zip=True,
        create_pdf=True,
        created_at="2026-06-16T00:00:00.000Z",
    )

    audit = audit_artifacts(
        run_dir=out_dir,
        package_dir=package_dir,
        zip_path=package_result.zip_path,
    )

    assert audit["status"] == "passed"
    assert audit["violations"] == []
    assert audit["counts"]["checked_run_artifacts"] >= 20
    assert audit["counts"]["checked_package_artifacts"] >= 20
    assert audit["counts"]["checked_zip_entries"] >= 20
    assert (package_dir / "analysis_report.pdf").exists()


def test_artifact_audit_reports_invalid_pdf_manifest(tmp_path):
    out_dir = _demo_output(tmp_path)
    package_dir = tmp_path / "analysis_package"
    create_analysis_package(
        input_dir=out_dir,
        output_dir=package_dir,
        create_pdf=True,
        created_at="2026-06-16T00:00:00.000Z",
    )
    manifest_path = package_dir / "export_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["pdf_export"]["redaction_status"] = "failed"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    audit = audit_artifacts(run_dir=out_dir, package_dir=package_dir)

    assert audit["status"] == "failed"
    assert any(
        violation["code"] == "PACKAGE_PDF_REDACTION_NOT_PASSED"
        for violation in audit["violations"]
    )


def test_artifact_audit_script_reports_pass(tmp_path):
    out_dir = _demo_output(tmp_path)
    package_dir = tmp_path / "analysis_package"
    package_result = create_analysis_package(
        input_dir=out_dir,
        output_dir=package_dir,
        create_zip=True,
        created_at="2026-06-16T00:00:00.000Z",
    )
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    python_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not python_path else f"src{os.pathsep}{python_path}"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_vsf_artifacts.py",
            "--run-dir",
            str(out_dir),
            "--package-dir",
            str(package_dir),
            "--zip-path",
            str(package_result.zip_path),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"status": "passed"' in result.stdout


def test_artifact_audit_reports_missing_artifact(tmp_path):
    out_dir = _demo_output(tmp_path)
    (out_dir / "relationship_graph.json").unlink()

    audit = audit_artifacts(run_dir=out_dir)

    assert audit["status"] == "failed"
    assert any(
        violation["code"] == "MISSING_RUN_ARTIFACT"
        and violation["path"] == "relationship_graph.json"
        for violation in audit["violations"]
    )


def test_artifact_audit_reports_raw_csv_and_connector_extracts(tmp_path):
    out_dir = _demo_output(tmp_path)
    (out_dir / "raw_source.csv").write_text("id,name\n1,Alice\n", encoding="utf-8")
    extract = out_dir / ".connector_extracts" / "postgres" / "orders.csv"
    extract.parent.mkdir(parents=True)
    extract.write_text("order_id\n1\n", encoding="utf-8")

    audit = audit_artifacts(run_dir=out_dir)
    codes = {violation["code"] for violation in audit["violations"]}

    assert audit["status"] == "failed"
    assert "RAW_CSV_NOT_ALLOWED" in codes
    assert "CONNECTOR_EXTRACT_NOT_ALLOWED" in codes


def test_artifact_audit_reports_secret_like_text(tmp_path):
    out_dir = _demo_output(tmp_path)
    (out_dir / "run.log").write_text(
        "failed password=super-secret postgresql://user:super-secret@127.0.0.1/db\n"
        "Authorization: Bearer abcdefghijklmnop\n"
        "key sk-test-secret-value-123456789\n",
        encoding="utf-8",
    )

    audit = audit_artifacts(run_dir=out_dir)
    codes = {violation["code"] for violation in audit["violations"]}

    assert audit["status"] == "failed"
    assert "UNREDACTED_SECRET_ASSIGNMENT" in codes
    assert "UNREDACTED_CONNECTION_URL" in codes
    assert "BEARER_TOKEN" in codes
    assert "OPENAI_KEY" in codes


def _demo_output(tmp_path: Path) -> Path:
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"
    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
    )
    return out_dir


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

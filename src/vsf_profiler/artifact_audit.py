from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from vsf_profiler.export_package import (
    BEARER_TOKEN_RE,
    CONNECTION_CREDENTIAL_RE,
    INDEX_NAME,
    MANIFEST_NAME,
    OPENAI_KEY_RE,
    PDF_REPORT_NAME,
    REQUIRED_ARTIFACTS,
    SENSITIVE_ASSIGNMENT_RE,
    TEXT_SUFFIXES,
)


REQUIRED_CHARTS = [
    "charts/dataset_verdict_risk_summary.json",
    "charts/influence_top_features.json",
    "charts/issue_counts_by_severity.json",
    "charts/issue_counts_by_type.json",
    "charts/missingness_by_table.json",
    "charts/missingness_top_columns.json",
    "charts/relationship_fk_health.json",
]
EXPECTED_ARTIFACT_PATHS = {
    "profile_summary": "profile_summary.json",
    "issues": "issues.json",
    "influence": "influence.json",
    "schema_parse_report": "schema_parse_report.json",
    "lineage_graph": "lineage_graph.json",
    "schema_evaluation": "schema_evaluation.json",
    "relationship_graph": "relationship_graph.json",
    "dataset_verdict": "dataset_verdict.json",
    "table_assessments": "table_assessments.json",
    "charts_dir": "charts",
    "chart_dataset_verdict_risk_summary": "charts/dataset_verdict_risk_summary.json",
    "chart_influence_top_features": "charts/influence_top_features.json",
    "chart_issue_counts_by_severity": "charts/issue_counts_by_severity.json",
    "chart_issue_counts_by_type": "charts/issue_counts_by_type.json",
    "chart_missingness_by_table": "charts/missingness_by_table.json",
    "chart_missingness_top_columns": "charts/missingness_top_columns.json",
    "chart_relationship_fk_health": "charts/relationship_fk_health.json",
    "schema_diagram_json": "schema_diagram.json",
    "schema_diagram_dbml": "schema_diagram.dbml",
    "report_md": "report.md",
    "report_html": "report.html",
    "run_log": "run.log",
    "run_events": "run_events.jsonl",
    "run_summary": "run_summary.json",
}
OPTIONAL_ARTIFACT_PATHS = {
    "connector_metadata": "connector_metadata.json",
    "l4_report": "l4_report.md",
    "guardrail_report": "guardrail_report.json",
    "samples_dir": "samples",
}
SCAN_SUFFIXES = TEXT_SUFFIXES


def audit_artifacts(
    *,
    run_dir: Path,
    package_dir: Path | None = None,
    zip_path: Path | None = None,
) -> dict[str, Any]:
    run_root = run_dir.resolve()
    package_root = package_dir.resolve() if package_dir else None
    zip_root = zip_path.resolve() if zip_path else None
    violations: list[dict[str, Any]] = []
    counts: dict[str, Any] = {
        "checked_run_artifacts": 0,
        "checked_package_artifacts": 0,
        "checked_text_files": 0,
        "checked_zip_entries": 0,
    }

    if not run_root.is_dir():
        violations.append(_violation("RUN_DIR_MISSING", str(run_dir), "Run directory does not exist."))
    else:
        _check_required_files(
            root=run_root,
            paths=[*REQUIRED_ARTIFACTS, *REQUIRED_CHARTS],
            code="MISSING_RUN_ARTIFACT",
            violations=violations,
        )
        counts["checked_run_artifacts"] = len(REQUIRED_ARTIFACTS) + len(REQUIRED_CHARTS)
        _check_run_summary(run_root, violations)
        _check_raw_csv_boundary(run_root, violations)
        counts["checked_text_files"] += _scan_secret_like_text(run_root, violations)

    if package_root is not None:
        if not package_root.is_dir():
            violations.append(
                _violation(
                    "PACKAGE_DIR_MISSING",
                    str(package_dir),
                    "Package directory does not exist.",
                )
            )
        else:
            package_required = [MANIFEST_NAME, INDEX_NAME, *REQUIRED_ARTIFACTS, *REQUIRED_CHARTS]
            _check_required_files(
                root=package_root,
                paths=package_required,
                code="MISSING_PACKAGE_ARTIFACT",
                violations=violations,
            )
            counts["checked_package_artifacts"] = len(package_required)
            _check_export_manifest(package_root, violations)
            _check_raw_csv_boundary(package_root, violations)
            counts["checked_text_files"] += _scan_secret_like_text(package_root, violations)

    if zip_root is not None:
        if not zip_root.is_file():
            violations.append(
                _violation("ZIP_MISSING", str(zip_path), "Package zip archive does not exist.")
            )
        else:
            _check_zip_archive(zip_root, violations, counts)

    return {
        "artifact": "artifact_audit_report",
        "status": "failed" if violations else "passed",
        "checked": {
            "run_dir": str(run_root),
            "package_dir": str(package_root) if package_root else None,
            "zip_path": str(zip_root) if zip_root else None,
        },
        "counts": counts,
        "violations": violations,
    }


def _check_required_files(
    *,
    root: Path,
    paths: list[str],
    code: str,
    violations: list[dict[str, Any]],
) -> None:
    for relative_path in paths:
        path = root / relative_path
        if not path.is_file():
            violations.append(
                _violation(code, relative_path, "Required generated artifact is missing.")
            )


def _check_run_summary(root: Path, violations: list[dict[str, Any]]) -> None:
    summary_path = root / "run_summary.json"
    summary = _read_json(summary_path)
    if not summary:
        violations.append(
            _violation("INVALID_RUN_SUMMARY", "run_summary.json", "Cannot parse run summary.")
        )
        return
    artifact_paths = summary.get("artifact_paths")
    if not isinstance(artifact_paths, dict):
        violations.append(
            _violation(
                "INVALID_RUN_SUMMARY",
                "run_summary.json",
                "artifact_paths must be an object.",
            )
        )
        return
    expected = dict(EXPECTED_ARTIFACT_PATHS)
    expected.update(
        {
            key: path
            for key, path in OPTIONAL_ARTIFACT_PATHS.items()
            if (root / path).exists() or key in artifact_paths
        }
    )
    for key, expected_path in expected.items():
        actual_path = artifact_paths.get(key)
        if actual_path != expected_path:
            violations.append(
                _violation(
                    "ARTIFACT_PATH_MISMATCH",
                    f"run_summary.json:{key}",
                    f"Expected {expected_path!r}, found {actual_path!r}.",
                )
            )


def _check_export_manifest(root: Path, violations: list[dict[str, Any]]) -> None:
    manifest = _read_json(root / MANIFEST_NAME)
    if not manifest:
        violations.append(
            _violation("INVALID_EXPORT_MANIFEST", MANIFEST_NAME, "Cannot parse export manifest.")
        )
        return
    redaction = manifest.get("redaction") if isinstance(manifest, dict) else {}
    if not isinstance(redaction, dict) or redaction.get("status") != "passed":
        violations.append(
            _violation(
                "PACKAGE_REDACTION_NOT_PASSED",
                MANIFEST_NAME,
                "Export manifest redaction status is not passed.",
            )
        )
    included = manifest.get("included_files")
    if isinstance(included, list):
        included_paths = {entry.get("path") for entry in included if isinstance(entry, dict)}
        for relative_path in [INDEX_NAME, *REQUIRED_ARTIFACTS, *REQUIRED_CHARTS]:
            if relative_path not in included_paths:
                violations.append(
                    _violation(
                        "PACKAGE_MANIFEST_MISSING_ENTRY",
                        relative_path,
                        "Export manifest is missing an included file entry.",
                    )
                )
        pdf_export = manifest.get("pdf_export")
        if isinstance(pdf_export, dict) and pdf_export.get("created"):
            _check_pdf_manifest_entry(root, pdf_export, included, included_paths, violations)


def _check_pdf_manifest_entry(
    root: Path,
    pdf_export: dict[str, Any],
    included: list[Any],
    included_paths: set[Any],
    violations: list[dict[str, Any]],
) -> None:
    if pdf_export.get("path") != PDF_REPORT_NAME:
        violations.append(
            _violation(
                "PACKAGE_PDF_MANIFEST_INVALID",
                MANIFEST_NAME,
                f"PDF export path must be {PDF_REPORT_NAME!r}.",
            )
        )
    if pdf_export.get("redaction_status") != "passed":
        violations.append(
            _violation(
                "PACKAGE_PDF_REDACTION_NOT_PASSED",
                PDF_REPORT_NAME,
                "PDF export redaction status is not passed.",
            )
        )
    if PDF_REPORT_NAME not in included_paths:
        violations.append(
            _violation(
                "PACKAGE_MANIFEST_MISSING_ENTRY",
                PDF_REPORT_NAME,
                "Export manifest is missing the PDF included file entry.",
            )
        )
        return
    pdf_path = root / PDF_REPORT_NAME
    if not pdf_path.is_file():
        violations.append(
            _violation("MISSING_PACKAGE_ARTIFACT", PDF_REPORT_NAME, "PDF report is missing.")
        )
        return
    included_entry = next(
        (entry for entry in included if isinstance(entry, dict) and entry.get("path") == PDF_REPORT_NAME),
        None,
    )
    expected_sha = included_entry.get("sha256") if isinstance(included_entry, dict) else ""
    if pdf_export.get("sha256") != expected_sha:
        violations.append(
            _violation(
                "PACKAGE_PDF_CHECKSUM_MISMATCH",
                PDF_REPORT_NAME,
                "PDF export checksum does not match included file entry.",
            )
        )


def _check_raw_csv_boundary(root: Path, violations: list[dict[str, Any]]) -> None:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = _relative_posix(path, root)
        parts = relative_path.split("/")
        if ".connector_extracts" in parts:
            violations.append(
                _violation(
                    "CONNECTOR_EXTRACT_NOT_ALLOWED",
                    relative_path,
                    "Connector temporary extract is not allowed in audited outputs.",
                )
            )
        if path.suffix.lower() == ".csv" and (not parts or parts[0] != "samples"):
            violations.append(
                _violation(
                    "RAW_CSV_NOT_ALLOWED",
                    relative_path,
                    "CSV files are only allowed under samples/.",
                )
            )


def _scan_secret_like_text(root: Path, violations: list[dict[str, Any]]) -> int:
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        scanned += 1
        relative_path = _relative_posix(path, root)
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            violations.extend(_secret_violations(relative_path, line_number, line))
    return scanned


def _secret_violations(path: str, line_number: int, line: str) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for match in CONNECTION_CREDENTIAL_RE.finditer(line):
        credential = match.group(2)
        if credential != "[redacted]":
            violations.append(_secret_violation(path, line_number, "UNREDACTED_CONNECTION_URL"))
    for match in SENSITIVE_ASSIGNMENT_RE.finditer(line):
        value = match.group(2)
        if value.lower() not in {"[redacted]", "%5bredacted%5d"}:
            violations.append(_secret_violation(path, line_number, "UNREDACTED_SECRET_ASSIGNMENT"))
    if BEARER_TOKEN_RE.search(line):
        violations.append(_secret_violation(path, line_number, "BEARER_TOKEN"))
    if OPENAI_KEY_RE.search(line):
        violations.append(_secret_violation(path, line_number, "OPENAI_KEY"))
    return violations


def _secret_violation(path: str, line_number: int, code: str) -> dict[str, Any]:
    return _violation(code, f"{path}:{line_number}", "Unredacted secret-like text found.")


def _check_zip_archive(
    zip_path: Path,
    violations: list[dict[str, Any]],
    counts: dict[str, Any],
) -> None:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            manifest = _read_manifest_from_zip(archive)
    except zipfile.BadZipFile:
        violations.append(_violation("INVALID_ZIP", zip_path.name, "Zip archive cannot be read."))
        return
    counts["checked_zip_entries"] = len(names)
    required = [MANIFEST_NAME, INDEX_NAME, *REQUIRED_ARTIFACTS, *REQUIRED_CHARTS]
    pdf_export = manifest.get("pdf_export") if isinstance(manifest, dict) else {}
    if isinstance(pdf_export, dict) and pdf_export.get("created"):
        required.append(PDF_REPORT_NAME)
    for relative_path in required:
        if relative_path not in names:
            violations.append(
                _violation(
                    "ZIP_MISSING_ENTRY",
                    relative_path,
                    "Package zip is missing a required entry.",
                )
            )
    for name in names:
        parts = name.split("/")
        if ".connector_extracts" in parts:
            violations.append(
                _violation(
                    "ZIP_CONNECTOR_EXTRACT_NOT_ALLOWED",
                    name,
                    "Connector temporary extract is not allowed in package zip.",
                )
            )
        if Path(name).suffix.lower() == ".csv" and (not parts or parts[0] != "samples"):
            violations.append(
                _violation(
                    "ZIP_RAW_CSV_NOT_ALLOWED",
                    name,
                    "Zip CSV files are only allowed under samples/.",
                )
            )


def _read_manifest_from_zip(archive: zipfile.ZipFile) -> dict[str, Any]:
    if MANIFEST_NAME not in archive.namelist():
        return {}
    try:
        payload = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _violation(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}

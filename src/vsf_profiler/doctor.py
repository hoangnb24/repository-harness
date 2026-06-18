from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from vsf_profiler.connectors import DEFAULT_MYSQL_URL_ENV, DEFAULT_POSTGRES_URL_ENV
from vsf_profiler.pdf_export import PDF_BACKEND


CapabilityStatus = Literal["ok", "failed", "missing", "skipped"]
CapabilityKind = Literal["required", "optional"]

REQUIRED_IMPORTS = {
    "duckdb": "DuckDB query engine",
    "jinja2": "Jinja report templates",
    "pandas": "bounded dataframe materialization",
    "pydantic": "artifact contracts",
    "typer": "CLI runtime",
    "yaml": "YAML rules parser",
}
POSTGRES_ENV_NAMES = (DEFAULT_POSTGRES_URL_ENV, "VSF_POSTGRES_TEST_URL")
MYSQL_ENV_NAMES = (DEFAULT_MYSQL_URL_ENV, "VSF_MYSQL_TEST_URL")


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    kind: CapabilityKind
    status: CapabilityStatus
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    checks: list[DoctorCheck]

    @property
    def status(self) -> str:
        return "failed" if has_required_failures(self) else "ok"


def build_doctor_report() -> DoctorReport:
    checks: list[DoctorCheck] = []
    checks.append(_python_version_check())
    checks.extend(_required_import_checks())
    checks.append(_duckdb_runtime_check())
    checks.extend(_optional_postgres_checks())
    checks.extend(_optional_mysql_checks())
    checks.append(_optional_pdf_check())
    checks.extend(_optional_node_checks())
    checks.extend(_optional_openai_checks())
    return DoctorReport(checks=checks)


def format_doctor_report(report: DoctorReport) -> str:
    lines = ["VSF Data Profiler doctor"]
    for check in report.checks:
        lines.append(f"[{check.status}] {check.kind} {check.name}: {check.detail}")
    lines.append(f"Doctor result: {report.status}")
    return "\n".join(lines)


def has_required_failures(report: DoctorReport) -> bool:
    return any(
        check.kind == "required" and check.status in {"failed", "missing"}
        for check in report.checks
    )


def _python_version_check() -> DoctorCheck:
    version = sys.version_info
    version_text = f"{version.major}.{version.minor}.{version.micro}"
    if version >= (3, 11):
        return DoctorCheck(
            name="python",
            kind="required",
            status="ok",
            detail=f"{version_text} satisfies >=3.11",
        )
    return DoctorCheck(
        name="python",
        kind="required",
        status="failed",
        detail=f"{version_text} is older than required >=3.11",
    )


def _required_import_checks() -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    for module_name, label in REQUIRED_IMPORTS.items():
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    name=f"import {module_name}",
                    kind="required",
                    status="missing",
                    detail=f"{label} unavailable: {exc.__class__.__name__}",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name=f"import {module_name}",
                    kind="required",
                    status="ok",
                    detail=label,
                )
            )
    return checks


def _duckdb_runtime_check() -> DoctorCheck:
    try:
        duckdb = importlib.import_module("duckdb")
        con = duckdb.connect(database=":memory:")
        try:
            value = con.execute("select 1").fetchone()[0]
        finally:
            con.close()
    except Exception as exc:
        return DoctorCheck(
            name="duckdb runtime",
            kind="required",
            status="failed",
            detail=f"cannot execute a memory query: {exc.__class__.__name__}",
        )
    if value != 1:
        return DoctorCheck(
            name="duckdb runtime",
            kind="required",
            status="failed",
            detail="unexpected query result",
        )
    return DoctorCheck(
        name="duckdb runtime",
        kind="required",
        status="ok",
        detail="memory query succeeded",
    )


def _optional_postgres_checks() -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    env_names = [name for name in POSTGRES_ENV_NAMES if os.environ.get(name, "").strip()]
    env_detail = (
        f"{', '.join(env_names)} present (redacted)"
        if env_names
        else f"no URL env configured ({', '.join(POSTGRES_ENV_NAMES)})"
    )
    checks.append(
        DoctorCheck(
            name="postgres env",
            kind="optional",
            status="ok" if env_names else "skipped",
            detail=env_detail,
        )
    )
    try:
        importlib.import_module("psycopg")
    except Exception as exc:
        checks.append(
            DoctorCheck(
                name="psycopg import",
                kind="optional",
                status="missing" if env_names else "skipped",
                detail=f"Postgres connector package unavailable: {exc.__class__.__name__}",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                name="psycopg import",
                kind="optional",
                status="ok",
                detail="Postgres connector package available",
            )
        )
    return checks


def _optional_mysql_checks() -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    env_names = [name for name in MYSQL_ENV_NAMES if os.environ.get(name, "").strip()]
    env_detail = (
        f"{', '.join(env_names)} present (redacted)"
        if env_names
        else f"no URL env configured ({', '.join(MYSQL_ENV_NAMES)})"
    )
    checks.append(
        DoctorCheck(
            name="mysql env",
            kind="optional",
            status="ok" if env_names else "skipped",
            detail=env_detail,
        )
    )
    try:
        importlib.import_module("pymysql")
    except Exception as exc:
        checks.append(
            DoctorCheck(
                name="pymysql import",
                kind="optional",
                status="missing" if env_names else "skipped",
                detail=f"MySQL connector package unavailable: {exc.__class__.__name__}",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                name="pymysql import",
                kind="optional",
                status="ok",
                detail="MySQL connector package available",
            )
        )
    return checks


def _optional_pdf_check() -> DoctorCheck:
    return DoctorCheck(
        name="pdf export backend",
        kind="optional",
        status="ok",
        detail=f"{PDF_BACKEND} available",
    )


def _optional_node_checks() -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    node_path = shutil.which("node")
    if node_path is None:
        return [
            DoctorCheck(
                name="node",
                kind="optional",
                status="skipped",
                detail="node executable not found",
            ),
            DoctorCheck(
                name="playwright",
                kind="optional",
                status="skipped",
                detail="node executable not found",
            ),
        ]
    node_version = _run_version([node_path, "--version"])
    checks.append(
        DoctorCheck(
            name="node",
            kind="optional",
            status="ok" if node_version else "failed",
            detail=node_version or "node --version failed",
        )
    )
    playwright_command = _playwright_command()
    if playwright_command is None:
        checks.append(
            DoctorCheck(
                name="playwright",
                kind="optional",
                status="skipped",
                detail="local Playwright executable not found",
            )
        )
    else:
        playwright_version = _run_version([*playwright_command, "--version"])
        checks.append(
            DoctorCheck(
                name="playwright",
                kind="optional",
                status="ok" if playwright_version else "failed",
                detail=playwright_version or "Playwright version check failed",
            )
        )
    return checks


def _optional_openai_checks() -> list[DoctorCheck]:
    env_file_values = _dotenv_values()
    key_present = bool(_env_or_dotenv("OPENAI_API_KEY", env_file_values))
    provider = _env_or_dotenv("VSF_PROFILER_LLM_PROVIDER", env_file_values)
    checks = [
        DoctorCheck(
            name="openai env",
            kind="optional",
            status="ok" if key_present else "skipped",
            detail="OPENAI_API_KEY present (redacted)"
            if key_present
            else "OPENAI_API_KEY not configured",
        )
    ]
    if provider:
        checks.append(
            DoctorCheck(
                name="llm provider env",
                kind="optional",
                status="ok",
                detail="VSF_PROFILER_LLM_PROVIDER present",
            )
        )
    return checks


def _env_or_dotenv(name: str, dotenv_values: dict[str, str]) -> str:
    return os.environ.get(name, "").strip() or dotenv_values.get(name, "").strip()


def _dotenv_values(path: Path = Path(".env")) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _playwright_command() -> list[str] | None:
    local_playwright = shutil.which("playwright")
    if local_playwright:
        return [local_playwright]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--no-install", "playwright"]
    return None


def _run_version(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return (result.stdout or result.stderr).strip().splitlines()[0]

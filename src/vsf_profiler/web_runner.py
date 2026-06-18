from __future__ import annotations

import json
import mimetypes
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


LOCAL_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8765
DEFAULT_RUN_ROOT = Path("outputs/web_runs")
MAX_UPLOAD_BYTES = 250 * 1024 * 1024
MAX_PATH_JOB_BYTES = 16 * 1024
TARGET_PATTERN = re.compile(r"^[A-Za-z_][\w]*\.[A-Za-z_][\w]*$")

ARTIFACT_LABELS = {
    "profile_summary.json": "Profile summary",
    "issues.json": "Issues",
    "connector_metadata.json": "Connector metadata",
    "schema_parse_report.json": "Schema parse diagnostics",
    "lineage_graph.json": "Lineage graph",
    "schema_evaluation.json": "Schema evaluation",
    "relationship_graph.json": "Relationship graph",
    "dataset_verdict.json": "EDA readiness",
    "table_assessments.json": "Table assessments",
    "influence.json": "Influence",
    "report.html": "HTML report",
    "report.md": "Markdown report",
    "run_events.jsonl": "Runtime events",
    "run_summary.json": "Runtime summary",
    "l4_report.md": "L4 narrative",
    "guardrail_report.json": "Guardrail report",
}
OPTIONAL_DASHBOARD_ARTIFACTS = [
    "connector_metadata.json",
    "l4_report.md",
    "guardrail_report.json",
]
DASHBOARD_REQUIRED_ARTIFACTS = [
    "issues.json",
    "schema_parse_report.json",
    "lineage_graph.json",
    "profile_summary.json",
    "relationship_graph.json",
    "dataset_verdict.json",
    "table_assessments.json",
    "schema_evaluation.json",
    "influence.json",
    "run_summary.json",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class UploadedFile:
    filename: str
    content: bytes


@dataclass
class WebRunJob:
    job_id: str
    root_dir: Path
    input_dir: Path
    csv_dir: Path
    out_dir: Path
    input_mode: str = "upload"
    status: str = "queued"
    created_at: str = field(default_factory=_iso_now)
    started_at: str | None = None
    finished_at: str | None = None
    error: str = ""

    @property
    def events_path(self) -> Path:
        return self.out_dir / "run_events.jsonl"

    @property
    def summary_path(self) -> Path:
        return self.out_dir / "run_summary.json"


class WebRunStore:
    def __init__(self, *, run_root: Path = DEFAULT_RUN_ROOT) -> None:
        self.run_root = run_root
        self.run_root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, WebRunJob] = {}
        self._lock = threading.Lock()

    def start_job(
        self,
        *,
        dbml: UploadedFile,
        csv_files: list[UploadedFile],
        rules: UploadedFile | None = None,
        target: str | None = None,
        mapping_overrides: dict[str, str] | None = None,
    ) -> WebRunJob:
        if not csv_files:
            raise ValueError("At least one CSV file is required.")
        job_id = _new_job_id()
        root_dir = self.run_root / job_id
        input_dir = root_dir / "input"
        csv_dir = input_dir / "csv"
        out_dir = root_dir / "artifacts"
        csv_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        dbml_path = input_dir / _safe_filename(dbml.filename, fallback="schema.dbml")
        dbml_path.write_bytes(dbml.content)
        stored_csv_names: dict[str, str] = {}
        for index, csv_file in enumerate(csv_files, start=1):
            fallback = f"table_{index}.csv"
            safe_name = _safe_filename(csv_file.filename, fallback=fallback)
            (csv_dir / safe_name).write_bytes(csv_file.content)
            stored_csv_names[csv_file.filename] = safe_name
            stored_csv_names[Path(csv_file.filename).stem] = Path(safe_name).stem
        rules_path: Path | None = None
        if rules is not None and rules.content.strip():
            rules_path = input_dir / _safe_filename(rules.filename, fallback="rules.yaml")
            rules_path.write_bytes(rules.content)
        stored_mapping_overrides = _translate_uploaded_mapping_overrides(
            _clean_mapping_overrides(mapping_overrides or {}),
            stored_csv_names=stored_csv_names,
        )

        job = WebRunJob(
            job_id=job_id,
            root_dir=root_dir,
            input_dir=input_dir,
            csv_dir=csv_dir,
            out_dir=out_dir,
            input_mode="upload",
        )
        with self._lock:
            self._jobs[job_id] = job
        thread = threading.Thread(
            target=self._run_job,
            args=(job, dbml_path, csv_dir, rules_path, target or None, stored_mapping_overrides),
            name=f"vsf-web-run-{job_id}",
            daemon=True,
        )
        thread.start()
        return job

    def start_path_job(
        self,
        *,
        dbml_path: str | Path,
        csv_dir: str | Path,
        rules_path: str | Path | None = None,
        target: str | None = None,
        mapping_overrides: dict[str, str] | None = None,
    ) -> WebRunJob:
        validated_dbml_path = _validated_file_path(
            dbml_path,
            label="DBML path",
            extensions={".dbml"},
        )
        validated_csv_dir = _validated_csv_dir(csv_dir)
        validated_rules_path: Path | None = None
        if rules_path is not None and str(rules_path).strip():
            validated_rules_path = _validated_file_path(
                rules_path,
                label="Rules path",
                extensions={".yaml", ".yml"},
            )
        validated_target = _validated_target(target)

        job_id = _new_job_id()
        root_dir = self.run_root / job_id
        input_dir = root_dir / "input"
        out_dir = root_dir / "artifacts"
        input_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "input_mode": "path",
            "dbml_path": str(validated_dbml_path),
            "csv_dir": str(validated_csv_dir),
            "rules_path": str(validated_rules_path) if validated_rules_path else None,
            "target": validated_target,
            "mapping_overrides": _clean_mapping_overrides(mapping_overrides or {}),
        }
        (input_dir / "path_inputs.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        job = WebRunJob(
            job_id=job_id,
            root_dir=root_dir,
            input_dir=input_dir,
            csv_dir=validated_csv_dir,
            out_dir=out_dir,
            input_mode="path",
        )
        with self._lock:
            self._jobs[job_id] = job
        thread = threading.Thread(
            target=self._run_job,
            args=(
                job,
                validated_dbml_path,
                validated_csv_dir,
                validated_rules_path,
                validated_target,
                _clean_mapping_overrides(mapping_overrides or {}),
            ),
            name=f"vsf-web-run-{job_id}",
            daemon=True,
        )
        thread.start()
        return job

    def get_job(self, job_id: str) -> WebRunJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def job_payload(self, job: WebRunJob) -> dict[str, Any]:
        summary = _read_json_if_exists(job.summary_path)
        return {
            "job_id": job.job_id,
            "status": job.status,
            "input_mode": job.input_mode,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "error": job.error,
            "summary": summary,
            "events_url": f"/api/jobs/{job.job_id}/events",
            "artifacts_url": f"/api/jobs/{job.job_id}/artifacts",
            "artifacts": self.artifact_payload(job),
        }

    def artifact_payload(self, job: WebRunJob) -> list[dict[str, str]]:
        artifacts: list[dict[str, str]] = []
        summary = _read_json_if_exists(job.summary_path)
        paths: set[str] = set()
        if summary:
            paths.update(
                path
                for path in (summary.get("artifact_paths") or {}).values()
                if isinstance(path, str)
            )
        for path in _canonical_artifact_paths(job.out_dir):
            paths.add(path)
        for artifact_path in sorted(paths):
            path = job.out_dir / artifact_path
            if not path.is_file():
                continue
            artifacts.append(
                {
                    "path": artifact_path,
                    "label": ARTIFACT_LABELS.get(artifact_path, artifact_path),
                    "url": f"/api/jobs/{job.job_id}/artifacts/{artifact_path}",
                }
            )
        return artifacts

    def dashboard_payload(self, job: WebRunJob) -> dict[str, Any]:
        artifacts = {artifact["path"]: artifact["url"] for artifact in self.artifact_payload(job)}
        chart_artifacts = sorted(path for path in artifacts if path.startswith("charts/"))
        missing_artifacts = [
            artifact_path
            for artifact_path in DASHBOARD_REQUIRED_ARTIFACTS
            if artifact_path not in artifacts
        ]
        return {
            "job_id": job.job_id,
            "status": job.status,
            "artifact_urls": {
                artifact_path: artifacts[artifact_path]
                for artifact_path in sorted(
                    set(DASHBOARD_REQUIRED_ARTIFACTS)
                    | set(chart_artifacts)
                    | set(OPTIONAL_DASHBOARD_ARTIFACTS)
                )
                if artifact_path in artifacts
            },
            "required_artifacts": list(DASHBOARD_REQUIRED_ARTIFACTS),
            "chart_artifacts": chart_artifacts,
            "missing_artifacts": missing_artifacts,
        }

    def resolve_artifact(self, job: WebRunJob, artifact_path: str) -> Path:
        decoded = unquote(artifact_path)
        candidate = (job.out_dir / decoded).resolve()
        root = job.out_dir.resolve()
        if candidate == root or root not in candidate.parents:
            raise ValueError("Artifact path is outside the job output directory.")
        if not candidate.is_file():
            raise FileNotFoundError(decoded)
        return candidate

    def _run_job(
        self,
        job: WebRunJob,
        dbml_path: Path,
        csv_dir: Path,
        rules_path: Path | None,
        target: str | None,
        mapping_overrides: dict[str, str] | None,
    ) -> None:
        from vsf_profiler.cli import run_pipeline

        job.status = "running"
        job.started_at = _iso_now()
        try:
            run_pipeline(
                dbml_path=dbml_path,
                csv_dir=csv_dir,
                mapping_overrides=mapping_overrides,
                rules_path=rules_path,
                target=target,
                out_dir=job.out_dir,
            )
        except Exception as exc:
            job.status = "failed"
            job.error = f"{exc.__class__.__name__}: {exc}"
        else:
            job.status = "succeeded"
        finally:
            job.finished_at = _iso_now()


class WebRunnerHandler(BaseHTTPRequestHandler):
    store: WebRunStore
    static_dir: Path

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._send_json({"status": "ok", "host": LOCAL_WEB_HOST})
            return
        if path.startswith("/api/jobs/"):
            self._handle_job_get(path)
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/jobs":
                payload = self._parse_multipart_upload()
                job = self.store.start_job(
                    dbml=payload["dbml"],
                    csv_files=payload["csv_files"],
                    rules=payload.get("rules"),
                    target=payload.get("target"),
                    mapping_overrides=payload.get("mapping_overrides"),
                )
            elif parsed.path == "/api/path-jobs":
                payload = self._parse_path_job_body()
                job = self.store.start_path_job(
                    dbml_path=payload["dbml_path"],
                    csv_dir=payload["csv_dir"],
                    rules_path=payload.get("rules_path"),
                    target=payload.get("target"),
                    mapping_overrides=payload.get("mapping_overrides"),
                )
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json(self.store.job_payload(job), status=HTTPStatus.ACCEPTED)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_job_get(self, path: str) -> None:
        parts = path.strip("/").split("/")
        if len(parts) < 3:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        job = self.store.get_job(parts[2])
        if job is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if len(parts) == 3:
            self._send_json(self.store.job_payload(job))
            return
        if len(parts) == 4 and parts[3] == "events":
            self._stream_events(job)
            return
        if len(parts) == 4 and parts[3] == "artifacts":
            self._send_json({"artifacts": self.store.artifact_payload(job)})
            return
        if len(parts) == 4 and parts[3] == "dashboard":
            self._send_json(self.store.dashboard_payload(job))
            return
        if len(parts) >= 5 and parts[3] == "artifacts":
            artifact_path = "/".join(parts[4:])
            try:
                path_to_file = self.store.resolve_artifact(job, artifact_path)
            except FileNotFoundError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            self._send_file(path_to_file)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _stream_events(self, job: WebRunJob) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        offset = 0
        try:
            while True:
                if job.events_path.exists():
                    with job.events_path.open("r", encoding="utf-8") as handle:
                        handle.seek(offset)
                        for line in handle:
                            self._write_sse("run-event", line.strip())
                        offset = handle.tell()
                self._write_sse("job", json.dumps(self.store.job_payload(job), ensure_ascii=False))
                if job.status in {"succeeded", "failed"}:
                    break
                time.sleep(0.4)
        except BrokenPipeError:
            return

    def _write_sse(self, event_name: str, data: str) -> None:
        try:
            self.wfile.write(f"event: {event_name}\n".encode("utf-8"))
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
        except BrokenPipeError:
            raise

    def _parse_multipart_upload(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Expected multipart/form-data upload.")
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Upload body is empty.")
        if content_length > MAX_UPLOAD_BYTES:
            raise ValueError("Upload is too large for demo mode.")
        body = self.rfile.read(content_length)
        header = (
            f"Content-Type: {content_type}\r\n"
            "MIME-Version: 1.0\r\n"
            "\r\n"
        ).encode("utf-8")
        message = BytesParser(policy=default).parsebytes(header + body)
        if not message.is_multipart():
            raise ValueError("Upload payload is not multipart.")

        dbml: UploadedFile | None = None
        rules: UploadedFile | None = None
        csv_files: list[UploadedFile] = []
        fields: dict[str, str] = {}

        for part in message.iter_parts():
            field_name = part.get_param("name", header="content-disposition")
            filename = part.get_filename()
            if not field_name:
                continue
            content = part.get_payload(decode=True) or b""
            if filename:
                upload = UploadedFile(filename=filename, content=content)
                if field_name == "dbml":
                    dbml = upload
                elif field_name == "rules":
                    rules = upload
                elif field_name in {"csv", "csvFiles"}:
                    csv_files.append(upload)
            else:
                charset = part.get_content_charset() or "utf-8"
                fields[field_name] = content.decode(charset, errors="replace").strip()

        if dbml is None:
            raise ValueError("DBML file is required.")
        return {
            "dbml": dbml,
            "csv_files": csv_files,
            "rules": rules,
            "target": fields.get("target") or None,
            "mapping_overrides": _parse_mapping_overrides_field(fields.get("mapping_overrides")),
        }

    def _parse_path_job_body(self) -> dict[str, str | None]:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ValueError("Expected application/json path job payload.")
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Path job body is empty.")
        if content_length > MAX_PATH_JOB_BYTES:
            raise ValueError("Path job payload is too large.")
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Path job payload must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Path job payload must be a JSON object.")
        return {
            "dbml_path": _required_string(payload, "dbml_path"),
            "csv_dir": _required_string(payload, "csv_dir"),
            "rules_path": _optional_string(payload, "rules_path"),
            "target": _optional_string(payload, "target"),
            "mapping_overrides": _optional_mapping_overrides(payload, "mapping_overrides"),
        }

    def _serve_static(self, path: str) -> None:
        if path in {"", "/"}:
            static_path = self.static_dir / "index.html"
        else:
            requested = unquote(path.lstrip("/"))
            static_path = (self.static_dir / requested).resolve()
            root = self.static_dir.resolve()
            if static_path == root or root not in static_path.parents:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
        if not static_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_file(static_path)

    def _send_file(self, path: Path) -> None:
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        with path.open("rb") as handle:
            self.wfile.write(handle.read())

    def _send_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_web_server(*, port: int = DEFAULT_WEB_PORT, run_root: Path = DEFAULT_RUN_ROOT) -> None:
    server = create_web_server(port=port, run_root=run_root)
    print(f"VSF Data Profiler web runner: http://{LOCAL_WEB_HOST}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def create_web_server(
    *,
    port: int = DEFAULT_WEB_PORT,
    run_root: Path = DEFAULT_RUN_ROOT,
) -> ThreadingHTTPServer:
    static_dir = _web_static_dir()
    store = WebRunStore(run_root=run_root)

    class Handler(WebRunnerHandler):
        pass

    Handler.store = store
    Handler.static_dir = static_dir
    return ThreadingHTTPServer((LOCAL_WEB_HOST, port), Handler)


def _web_static_dir() -> Path:
    repo_web = Path(__file__).resolve().parents[2] / "web"
    if repo_web.exists():
        return repo_web
    return Path.cwd() / "web"


def _canonical_artifact_paths(out_dir: Path) -> list[str]:
    paths = [
        "profile_summary.json",
        "issues.json",
        "schema_parse_report.json",
        "connector_metadata.json",
        "lineage_graph.json",
        "schema_evaluation.json",
        "relationship_graph.json",
        "dataset_verdict.json",
        "table_assessments.json",
        "influence.json",
        "schema_diagram.json",
        "schema_diagram.dbml",
        "run_events.jsonl",
        "run_summary.json",
        "run.log",
        "report.md",
        "report.html",
        "l4_report.md",
        "guardrail_report.json",
    ]
    chart_dir = out_dir / "charts"
    if chart_dir.exists():
        paths.extend(
            path.relative_to(out_dir).as_posix()
            for path in sorted(chart_dir.glob("*.json"))
        )
    return paths


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _validated_file_path(
    path_value: str | Path,
    *,
    label: str,
    extensions: set[str],
) -> Path:
    path = Path(path_value).expanduser()
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} must be a file: {path}")
    suffix = path.suffix.lower()
    if suffix not in extensions:
        allowed = ", ".join(sorted(extensions))
        raise ValueError(f"{label} must use {allowed} extension: {path}")
    return path.resolve()


def _validated_csv_dir(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.exists():
        raise ValueError(f"CSV directory does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"CSV directory must be a directory: {path}")
    if not any(child.is_file() and child.suffix.lower() == ".csv" for child in path.iterdir()):
        raise ValueError(f"CSV directory must contain at least one .csv file: {path}")
    return path.resolve()


def _validated_target(target: str | None) -> str | None:
    if target is None:
        return None
    stripped = target.strip()
    if not stripped:
        return None
    if not TARGET_PATTERN.match(stripped):
        raise ValueError("Target column must use table.column format.")
    return stripped


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required.")
    return value.strip()


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    stripped = value.strip()
    return stripped or None


def _optional_mapping_overrides(payload: dict[str, Any], key: str) -> dict[str, str]:
    value = payload.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object.")
    return _clean_mapping_overrides(value)


def _parse_mapping_overrides_field(value: str | None) -> dict[str, str]:
    if value is None or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("mapping_overrides must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("mapping_overrides must be a JSON object.")
    return _clean_mapping_overrides(parsed)


def _clean_mapping_overrides(mapping_overrides: dict[str, Any]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for table_name, csv_name in mapping_overrides.items():
        if not isinstance(table_name, str) or not table_name.strip():
            raise ValueError("Mapping override table names must be non-empty strings.")
        if not isinstance(csv_name, str) or not csv_name.strip():
            raise ValueError(f"Mapping override for {table_name!r} must be a non-empty string.")
        cleaned[table_name.strip()] = csv_name.strip()
    return cleaned


def _translate_uploaded_mapping_overrides(
    mapping_overrides: dict[str, str],
    *,
    stored_csv_names: dict[str, str],
) -> dict[str, str]:
    translated: dict[str, str] = {}
    for table_name, csv_name in mapping_overrides.items():
        translated[table_name] = stored_csv_names.get(csv_name, csv_name)
    return translated


def _safe_filename(filename: str, *, fallback: str) -> str:
    name = Path(filename).name.strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = name.strip("._")
    return name or fallback


def _new_job_id() -> str:
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"

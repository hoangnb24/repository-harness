from __future__ import annotations

import json
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any

from vsf_profiler.models import Issue, RunEvent, RunStageSummary, RunSummary


MAX_DETAIL_STRING_CHARS = 300
MAX_DETAIL_ITEMS = 20
SENSITIVE_KEY_PARTS = ("secret", "token", "credential", "password", "api_key")
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(password|passwd|pwd|token|api[_-]?key|secret)=([^\s,;]+)"
)
CONNECTION_URL_RE = re.compile(
    r"(?i)((?:postgres(?:ql)?|mysql|mariadb|mysql\+pymysql|mariadb\+pymysql)://)([^@\s]+)@"
)


class RuntimeStage:
    def __init__(self, runtime: RuntimeRecorder, name: str, display_name: str) -> None:
        self._runtime = runtime
        self.name = name
        self.display_name = display_name
        self._record: RunStageSummary | None = None
        self._started_monotonic: float | None = None
        self._details: dict[str, Any] = {}
        self._skip_reason: str | None = None

    def __enter__(self) -> RuntimeStage:
        self._started_monotonic = time.perf_counter()
        self._record = RunStageSummary(
            name=self.name,
            display_name=self.display_name,
            status="running",
            started_at=_iso_now(),
        )
        self._runtime._stage_started(self._record)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._record is None or self._started_monotonic is None:
            return False
        if exc is not None:
            self._runtime._stage_finished(
                record=self._record,
                started_monotonic=self._started_monotonic,
                status="failed",
                details=self._details,
                error=exc,
            )
            return False

        status = "skipped" if self._skip_reason else "completed"
        details = dict(self._details)
        if self._skip_reason:
            details["skip_reason"] = self._skip_reason
        self._runtime._stage_finished(
            record=self._record,
            started_monotonic=self._started_monotonic,
            status=status,
            details=details,
            error=None,
        )
        return False

    def add_detail(self, key: str, value: Any) -> None:
        self._details[key] = value

    def mark_skipped(self, reason: str) -> None:
        self._skip_reason = reason


class RuntimeRecorder:
    def __init__(self, *, out_dir: Path, inputs: dict[str, Any]) -> None:
        self.out_dir = out_dir
        self.log_path = out_dir / "run.log"
        self.events_path = out_dir / "run_events.jsonl"
        self.summary_path = out_dir / "run_summary.json"
        self.run_id = uuid.uuid4().hex
        self.inputs = _sanitize(inputs)
        self.status = "initialized"
        self.started_at = _iso_now()
        self.finished_at: str | None = None
        self._started_monotonic = time.perf_counter()
        self._sequence = 0
        self._stages: list[RunStageSummary] = []
        self._artifact_paths: dict[str, str] = {}
        self._issue_counts: dict[str, Any] = {"total": 0, "by_severity": {}, "by_type": {}}
        self._log_handle = None
        self._event_handle = None

    def start(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._log_handle = self.log_path.open("w", encoding="utf-8")
        self._event_handle = self.events_path.open("w", encoding="utf-8")
        self.status = "running"
        self.started_at = _iso_now()
        self._started_monotonic = time.perf_counter()
        self.declare_artifact(self.log_path, key="run_log")
        self.declare_artifact(self.events_path, key="run_events")
        self.declare_artifact(self.summary_path, key="run_summary")
        self._log("run_started", run_id=self.run_id)
        self._emit_event(
            "run_started",
            status="running",
            details={"inputs": self.inputs, "output_dir": str(self.out_dir)},
        )

    def stage(self, name: str, display_name: str) -> RuntimeStage:
        return RuntimeStage(self, name, display_name)

    def declare_artifact(self, path: Path, *, key: str | None = None) -> None:
        self._artifact_paths[key or _artifact_key(path)] = self._relative_output_path(path)

    def artifact_written(
        self,
        path: Path,
        *,
        key: str | None = None,
        kind: str = "artifact",
        details: dict[str, Any] | None = None,
    ) -> None:
        artifact_key = key or _artifact_key(path)
        artifact_path = self._relative_output_path(path)
        self._artifact_paths[artifact_key] = artifact_path
        event_details = {"artifact": artifact_key, "kind": kind}
        if details:
            event_details.update(details)
        self._log("artifact_written", artifact=artifact_key, path=artifact_path, kind=kind)
        self._emit_event(
            "artifact_written",
            artifact_path=artifact_path,
            details=event_details,
        )

    def set_issue_counts(self, issues: list[Issue]) -> None:
        by_severity = Counter(issue.severity for issue in issues)
        by_type = Counter(issue.issue_type for issue in issues)
        self._issue_counts = {
            "total": len(issues),
            "by_severity": dict(sorted(by_severity.items())),
            "by_type": dict(sorted(by_type.items())),
        }

    def report_context(self, *, status: str | None = None) -> dict[str, Any]:
        summary = self._build_summary(status=status or self.status)
        return summary.model_dump(mode="json")

    def finish_success(self, *, issues: list[Issue]) -> None:
        self.set_issue_counts(issues)
        self.status = "success"
        self.finished_at = _iso_now()
        self._write_summary(status="success")
        self.artifact_written(self.summary_path, key="run_summary", kind="runtime_summary")
        self._emit_event(
            "run_finished",
            status="success",
            duration_seconds=self._duration_seconds(),
            details={"issue_count": self._issue_counts["total"]},
        )
        self._log(
            "run_finished",
            status="success",
            duration_seconds=self._duration_seconds(),
            issue_count=self._issue_counts["total"],
        )
        self._close()

    def finish_failed(self, exc: BaseException, *, issues: list[Issue] | None = None) -> None:
        if issues is not None:
            self.set_issue_counts(issues)
        self.status = "failed"
        self.finished_at = _iso_now()
        error = _error_details(exc)
        try:
            self._write_summary(status="failed", error=error)
            self.artifact_written(self.summary_path, key="run_summary", kind="runtime_summary")
            self._emit_event(
                "run_failed",
                status="failed",
                duration_seconds=self._duration_seconds(),
                details={"error": error},
            )
            self._log("run_failed", **error)
        except Exception as runtime_error:
            try:
                self._log(
                    "runtime_failure_summary_write_failed",
                    error_type=runtime_error.__class__.__name__,
                    error_message=_bounded_string(str(runtime_error)),
                )
            except Exception:
                pass
        finally:
            self._close()

    def _stage_started(self, record: RunStageSummary) -> None:
        self._stages.append(record)
        self._log("stage_started", stage=record.name, display_name=record.display_name)
        self._emit_event(
            "stage_started",
            stage=record.name,
            status="running",
            details={"display_name": record.display_name},
        )

    def _stage_finished(
        self,
        *,
        record: RunStageSummary,
        started_monotonic: float,
        status: str,
        details: dict[str, Any],
        error: BaseException | None,
    ) -> None:
        record.status = status
        record.finished_at = _iso_now()
        record.duration_seconds = round(time.perf_counter() - started_monotonic, 6)
        record.details = _sanitize(details)
        event_details: dict[str, Any] = {"display_name": record.display_name}
        if record.details:
            event_details["details"] = record.details
        event_type = "stage_finished"
        if error is not None:
            record.error_type = error.__class__.__name__
            record.error_message = _bounded_string(str(error))
            event_type = "stage_failed"
            event_details["error_type"] = record.error_type
            event_details["error_message"] = record.error_message

        self._log(
            event_type,
            stage=record.name,
            status=status,
            duration_seconds=record.duration_seconds,
        )
        self._emit_event(
            event_type,
            stage=record.name,
            status=status,
            duration_seconds=record.duration_seconds,
            details=event_details,
        )

    def _write_summary(
        self,
        *,
        status: str,
        error: dict[str, str] | None = None,
    ) -> None:
        summary = self._build_summary(status=status, error=error)
        self.summary_path.write_text(
            json.dumps(summary.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _build_summary(
        self,
        *,
        status: str,
        error: dict[str, str] | None = None,
    ) -> RunSummary:
        return RunSummary(
            run_id=self.run_id,
            status=status,
            started_at=self.started_at,
            finished_at=self.finished_at,
            duration_seconds=self._duration_seconds(),
            inputs=self.inputs,
            output_dir=str(self.out_dir),
            stage_timings=self._stages,
            issue_counts=self._issue_counts,
            artifact_paths=dict(sorted(self._artifact_paths.items())),
            skipped_stages=[
                _stage_detail(stage) for stage in self._stages if stage.status == "skipped"
            ],
            failed_stages=[
                _stage_detail(stage) for stage in self._stages if stage.status == "failed"
            ],
            error=error,
        )

    def _emit_event(
        self,
        event_type: str,
        *,
        stage: str | None = None,
        status: str | None = None,
        duration_seconds: float | None = None,
        artifact_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self._event_handle is None:
            return
        self._sequence += 1
        event = RunEvent(
            sequence=self._sequence,
            event_type=event_type,
            timestamp=_iso_now(),
            run_id=self.run_id,
            stage=stage,
            status=status,
            duration_seconds=duration_seconds,
            artifact_path=artifact_path,
            details=_sanitize(details or {}),
        )
        self._event_handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
        self._event_handle.write("\n")
        self._event_handle.flush()

    def _log(self, event: str, **fields: Any) -> None:
        if self._log_handle is None:
            return
        safe_fields = _sanitize(fields)
        pairs = " ".join(f"{key}={value}" for key, value in safe_fields.items())
        suffix = f" {pairs}" if pairs else ""
        self._log_handle.write(f"{_iso_now()} {event}{suffix}\n")
        self._log_handle.flush()

    def _relative_output_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.out_dir.resolve()))
        except ValueError:
            return str(path)

    def _duration_seconds(self) -> float:
        return round(time.perf_counter() - self._started_monotonic, 6)

    def _close(self) -> None:
        for handle in (self._event_handle, self._log_handle):
            if handle is not None:
                handle.close()
        self._event_handle = None
        self._log_handle = None


def _artifact_key(path: Path) -> str:
    name = path.name
    if name == "profile_summary.json":
        return "profile_summary"
    if name == "issues.json":
        return "issues"
    if name == "influence.json":
        return "influence"
    if name == "schema_diagram.json":
        return "schema_diagram_json"
    if name == "schema_diagram.dbml":
        return "schema_diagram_dbml"
    if name == "report.md":
        return "report_md"
    if name == "report.html":
        return "report_html"
    if name == "run.log":
        return "run_log"
    if name == "run_events.jsonl":
        return "run_events"
    if name == "run_summary.json":
        return "run_summary"
    return path.stem.replace("-", "_").replace(".", "_")


def _stage_detail(stage: RunStageSummary) -> dict[str, Any]:
    detail = {
        "name": stage.name,
        "display_name": stage.display_name,
        "status": stage.status,
        "duration_seconds": stage.duration_seconds,
        "details": stage.details,
    }
    if stage.error_type:
        detail["error_type"] = stage.error_type
    if stage.error_message:
        detail["error_message"] = stage.error_message
    return detail


def _error_details(exc: BaseException) -> dict[str, str]:
    return {
        "error_type": exc.__class__.__name__,
        "error_message": _bounded_string(str(exc)),
    }


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sanitize(value: Any, *, key: str | None = None) -> Any:
    if key and any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
        return "[redacted]"
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        return _bounded_string(value)
    if isinstance(value, Path):
        return _bounded_string(str(value))
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for index, (item_key, item_value) in enumerate(value.items()):
            if index >= MAX_DETAIL_ITEMS:
                sanitized["truncated"] = True
                break
            key_text = str(item_key)
            sanitized[key_text] = _sanitize(item_value, key=key_text)
        return sanitized
    if isinstance(value, list | tuple | set):
        items = list(value)
        sanitized_items = [_sanitize(item) for item in items[:MAX_DETAIL_ITEMS]]
        if len(items) > MAX_DETAIL_ITEMS:
            sanitized_items.append(f"... {len(items) - MAX_DETAIL_ITEMS} more")
        return sanitized_items
    return _bounded_string(str(value))


def _bounded_string(value: str) -> str:
    compact = _redact_sensitive_text(value).replace("\n", " ").replace("\r", " ")
    if len(compact) <= MAX_DETAIL_STRING_CHARS:
        return compact
    return compact[:MAX_DETAIL_STRING_CHARS] + "...[truncated]"


def _redact_sensitive_text(value: str) -> str:
    value = CONNECTION_URL_RE.sub(r"\1[redacted]@", value)
    return SENSITIVE_ASSIGNMENT_RE.sub(r"\1=[redacted]", value)

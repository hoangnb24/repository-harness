from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


BASELINE_DIR = Path("outputs/demo_small")
OPENAI_DIR = Path("outputs/demo_small_l4_openai_smoke")
BASELINE_MANIFEST = Path("outputs/demo_small_deterministic_manifest_before_openai.json")

DETERMINISTIC_ARTIFACTS = [
    "profile_summary.json",
    "issues.json",
    "influence.json",
    "schema_evaluation.json",
    "relationship_graph.json",
    "dataset_verdict.json",
    "table_assessments.json",
    "schema_diagram.json",
    "schema_diagram.dbml",
]


def main() -> None:
    _require(BASELINE_DIR.exists(), "baseline output directory is missing")
    _require(OPENAI_DIR.exists(), "OpenAI smoke output directory is missing")
    _require(BASELINE_MANIFEST.exists(), "baseline manifest is missing")

    guardrail = _read_json(OPENAI_DIR / "guardrail_report.json")
    _require((OPENAI_DIR / "l4_report.md").exists(), "l4_report.md is missing")
    _require(guardrail["provider"] == "openai", "guardrail provider is not openai")
    _require(guardrail["status"] == "passed", f"guardrail did not pass: {guardrail['status']}")
    _require(guardrail["fallback_reason"] == "", "OpenAI smoke used deterministic fallback")
    _require(guardrail.get("violation_count", 0) == 0, "guardrail violation_count is not zero")
    _require(not guardrail.get("violations"), "guardrail violations are not empty")
    _require(guardrail["raw_csv_included"] is False, "raw_csv_included flag is not false")
    _require(
        guardrail["unbounded_samples_included"] is False,
        "unbounded_samples_included flag is not false",
    )
    _require(guardrail["checked_numbers"], "guardrail checked_numbers is empty")
    _require(guardrail["checked_refs"], "guardrail checked_refs is empty")

    before = _read_json(BASELINE_MANIFEST)
    baseline_changed = [
        path
        for path, digest in before["hashes"].items()
        if _sha256(BASELINE_DIR / path) != digest
    ]
    _require(not baseline_changed, f"baseline artifacts changed: {baseline_changed}")

    openai_diffs = [
        path
        for path, digest in before["hashes"].items()
        if not (OPENAI_DIR / path).exists() or _sha256(OPENAI_DIR / path) != digest
    ]
    _require(not openai_diffs, f"OpenAI run changed deterministic core artifacts: {openai_diffs}")

    scan_files = [
        OPENAI_DIR / "run.log",
        OPENAI_DIR / "run_events.jsonl",
        OPENAI_DIR / "run_summary.json",
        OPENAI_DIR / "report.md",
        OPENAI_DIR / "report.html",
        OPENAI_DIR / "l4_report.md",
        OPENAI_DIR / "guardrail_report.json",
    ]
    scan_text = "\n".join(path.read_text(encoding="utf-8") for path in scan_files)
    secret = _env_values(Path(".env")).get("OPENAI_API_KEY", "").strip()
    secret_markers = ["OPENAI_API_KEY", "Authorization", "Bearer ", "sk-"]
    _require(not (secret and secret in scan_text), "actual OpenAI API key leaked into outputs")
    leaked_markers = [marker for marker in secret_markers if marker in scan_text]
    _require(not leaked_markers, f"secret marker leaked into outputs: {leaked_markers}")

    raw_row_hits = _raw_row_hits(scan_text)
    _require(not raw_row_hits, f"raw CSV row leaked into outputs: {raw_row_hits[:3]}")
    log_event_text = "\n".join(
        [
            (OPENAI_DIR / "run.log").read_text(encoding="utf-8"),
            (OPENAI_DIR / "run_events.jsonl").read_text(encoding="utf-8"),
        ]
    )
    prompt_markers = [
        "Generate the guarded L4 Senior Data Scientist narrative",
        "privacy_contract",
        "source_artifacts",
        "top_issues",
    ]
    leaked_prompt_markers = [marker for marker in prompt_markers if marker in log_event_text]
    _require(
        not leaked_prompt_markers,
        f"runtime logs/events contain prompt context markers: {leaked_prompt_markers}",
    )

    print("openai_smoke_verification=passed")
    print(f"guardrail_status={guardrail['status']}")
    print(f"fallback_reason={guardrail['fallback_reason'] or '<none>'}")
    print(f"violation_count={guardrail.get('violation_count', 0)}")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _raw_row_hits(scan_text: str) -> list[str]:
    hits = []
    for csv_path in sorted(Path("data/demo_small/csv").glob("*.csv")):
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                raw_line = ",".join(row)
                if raw_line and raw_line in scan_text:
                    hits.append(raw_line)
    return sorted(set(hits))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    main()

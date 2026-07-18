#!/usr/bin/env python3
"""Fail-closed Phase 6 framework and candidate-evidence verifier."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "tests" / "evals" / "v1-phase6"
EVIDENCE = EVAL / "evidence"
SCHEMAS = EVAL / "schemas"
SCHEMA_NAMES = (
    "baseline-lock",
    "candidate-result",
    "candidate-subject",
    "comparison-report",
    "condition-lock",
    "evidence-index",
    "intervention-log",
    "lane-assignment",
    "packet-manifest",
    "signature",
    "warm-v0-capture",
)
BASE_COMMIT = "5d6e6bc516cd60e47c60ae3b516363cd99b433a5"
NAMESPACE = "repository-harness-phase6"
ALL_CARDS = [f"P{number}" for number in range(8)]
WARM_CARDS = ["P0", "P1"]
MANDATORY_NEGATIVES = {
    "phase5-baseline-mutation",
    "condition-drift",
    "acceptance-test-failure",
    "unlogged-intervention",
    "target-data-loss",
    "raw-v0-evidence-custody",
    "held-out-hint-leakage",
    "candidate-functional-regression",
    "missing-applicability-finding",
    "gardening-scope-churn",
    "release-boundary-violation",
    "live-v0-source-mutation",
}
ALLOWED_CHANGED_FILES = {
    "scripts/capture-v1-phase6-warm-v0.py",
    "scripts/verify-v1-phase6-evidence.sh",
    "scripts/verify_v1_phase6_evidence.py",
    "tests/evals/test-v1-phase6-evidence.sh",
}
ALLOWED_CHANGED_PREFIXES = ("tests/evals/v1-phase6/",)
FORBIDDEN_PHASE6_FILENAMES = {
    "harness.db",
    "harness.db-wal",
    "harness.db-shm",
    "standalone-backup.sqlite",
    "archive.age",
    "archive.bin",
}


class VerificationError(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def proof(label: str, function: Callable[[], None]) -> None:
    function()
    print(f"Phase 6 proof passed: {label}")


def run(arguments: list[str], *, cwd: Path = ROOT, input_bytes: bytes | None = None) -> bytes:
    environment = dict(os.environ)
    for name in list(environment):
        if name.startswith("GIT_") or name.startswith("HARNESS_PHASE"):
            environment.pop(name, None)
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    result = subprocess.run(
        arguments,
        cwd=cwd,
        input=input_bytes,
        capture_output=True,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        raise VerificationError(
            f"command failed ({result.returncode}): {' '.join(arguments)}"
        )
    return result.stdout


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot load closed JSON record: {path}") from error


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise VerificationError(f"cannot hash evidence artifact: {path}") from error
    return digest.hexdigest()


def canonical_bytes(document: dict[str, Any], omitted: str | None = None) -> bytes:
    content = dict(document)
    if omitted is not None:
        content.pop(omitted, None)
    return json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_digest(document: dict[str, Any], omitted: str) -> str:
    return sha256_bytes(canonical_bytes(document, omitted))


def schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMAS / f"{name}.schema.json")


def type_matches(instance: Any, expected: str) -> bool:
    return {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
        "boolean": isinstance(instance, bool),
        "null": instance is None,
    }.get(expected, False)


def validate(instance: Any, contract: dict[str, Any], location: str = "$") -> None:
    if "const" in contract:
        check(instance == contract["const"], f"{location}: const mismatch")
    if "enum" in contract:
        check(instance in contract["enum"], f"{location}: value outside enum")
    expected = contract.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        check(
            any(type_matches(instance, item) for item in expected_types),
            f"{location}: wrong JSON type",
        )
    if isinstance(instance, dict):
        required = set(contract.get("required", []))
        check(required <= set(instance), f"{location}: missing {sorted(required - set(instance))}")
        properties = contract.get("properties", {})
        if contract.get("additionalProperties") is False:
            check(
                set(instance) <= set(properties),
                f"{location}: unknown fields {sorted(set(instance) - set(properties))}",
            )
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], f"{location}.{key}")
    if isinstance(instance, list):
        if "minItems" in contract:
            check(len(instance) >= contract["minItems"], f"{location}: too few items")
        if "maxItems" in contract:
            check(len(instance) <= contract["maxItems"], f"{location}: too many items")
        if "items" in contract:
            for index, value in enumerate(instance):
                validate(value, contract["items"], f"{location}[{index}]")
    if isinstance(instance, str):
        if "minLength" in contract:
            check(len(instance) >= contract["minLength"], f"{location}: string is empty")
        if "pattern" in contract:
            check(re.fullmatch(contract["pattern"], instance) is not None, f"{location}: pattern mismatch")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in contract:
            check(instance >= contract["minimum"], f"{location}: below minimum")
        if "maximum" in contract:
            check(instance <= contract["maximum"], f"{location}: above maximum")


def parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise VerificationError(f"{field}: invalid strict UTC timestamp") from error
    return parsed


def relative_name(value: str, field: str) -> PurePosixPath:
    candidate = PurePosixPath(value)
    check(not candidate.is_absolute(), f"{field}: absolute path is prohibited")
    check(all(part not in {"", ".", ".."} for part in candidate.parts), f"{field}: traversal is prohibited")
    check(str(candidate) == value and "\\" not in value, f"{field}: path is not canonical POSIX form")
    return candidate


def contained_member(root: Path, value: str, field: str) -> Path:
    relative = relative_name(value, field)
    candidate = root.joinpath(*relative.parts)
    check(candidate.exists() and candidate.is_file() and not candidate.is_symlink(), f"{field}: missing or unsafe member")
    check(candidate.resolve().is_relative_to(root.resolve()), f"{field}: member escaped custody")
    return candidate


def exact_cards(records: list[Any], expected: list[str], location: str) -> None:
    identifiers = [record if isinstance(record, str) else record.get("card_id") for record in records]
    check(identifiers == expected, f"{location}: expected exact ordered cards {expected}, got {identifiers}")


def validate_baseline_lock() -> dict[str, Any]:
    for name in SCHEMA_NAMES:
        definition = schema(name)
        check(definition.get("type") == "object", f"{name} schema must describe an object")
        check(
            definition.get("additionalProperties") is False,
            f"{name} schema must be closed at its root",
        )
        check(isinstance(definition.get("required"), list), f"{name} schema must declare required fields")
    path = EVAL / "baseline-lock.json"
    document = load_json(path)
    validate(document, schema("baseline-lock"), "baseline lock")
    check(document["lock_sha256"] == canonical_digest(document, "lock_sha256"), "baseline lock self-digest mismatch")
    check(document["source_commit"] == BASE_COMMIT, "baseline lock changed accepted source commit")
    check(len(document["protected_git_objects"]) == 4, "baseline lock protected-object set changed")
    check(len(document["pilots"]) == 2, "baseline lock must contain exactly two accepted pilots")
    return document


def git_oid(commit: str, path: str) -> str:
    return run(["git", "rev-parse", f"{commit}:{path}"]).decode("ascii").strip()


def verify_tree_against_worktree(commit: str, root: str) -> None:
    output = run(["git", "ls-tree", "-r", commit, "--", root]).decode("utf-8")
    expected: dict[str, str] = {}
    for line in output.splitlines():
        metadata, path = line.split("\t", 1)
        _, kind, oid = metadata.split(" ")
        check(kind == "blob", f"protected tree contains non-blob member: {path}")
        expected[path] = oid
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / root).rglob("*")
        if path.is_file() or path.is_symlink()
    }
    check(actual == set(expected), f"Phase 5 protected tree inventory changed under {root}")
    for path, oid in expected.items():
        candidate = ROOT / path
        check(not candidate.is_symlink(), f"Phase 5 protected path became a symlink: {path}")
        current_oid = run(["git", "hash-object", "--no-filters", path]).decode("ascii").strip()
        check(current_oid == oid, f"Phase 5 protected bytes changed: {path}")


def verify_phase5_immutability(lock: dict[str, Any]) -> None:
    for entry in lock["protected_git_objects"]:
        check(git_oid(lock["source_commit"], entry["path"]) == entry["git_oid"], f"frozen Git object mismatch: {entry['path']}")
        if entry["kind"] == "tree":
            verify_tree_against_worktree(lock["source_commit"], entry["path"])
        else:
            path = ROOT / entry["path"]
            check(path.is_file() and not path.is_symlink(), f"protected Phase 5 file missing: {entry['path']}")
            current_oid = run(["git", "hash-object", "--no-filters", entry["path"]]).decode("ascii").strip()
            check(current_oid == entry["git_oid"], f"protected Phase 5 file changed: {entry['path']}")
    check(sha256_file(ROOT / "tests/evals/v1-phase5/cards/catalog.json") == lock["card_catalog_sha256"], "Phase 5 card catalog digest changed")
    check(sha256_file(ROOT / "tests/evals/v1-phase5/evidence/index.json") == lock["phase5_evidence_index_sha256"], "Phase 5 evidence index digest changed")
    for pilot in lock["pilots"]:
        root = ROOT / "tests/evals/v1-phase5/evidence" / pilot["pilot_id"]
        check(sha256_file(root / "authentication.json") == pilot["authentication_sha256"], f"{pilot['pilot_id']} authentication changed")
        check(sha256_file(root / "packet-manifest.json") == pilot["packet_manifest_sha256"], f"{pilot['pilot_id']} packet manifest changed")
        check(sha256_file(root / "repository.bundle") == pilot["repository_bundle_sha256"], f"{pilot['pilot_id']} bundle changed")


def changed_paths() -> set[str]:
    tracked = run(["git", "diff", "--name-only", BASE_COMMIT, "--"]).decode("utf-8").splitlines()
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"]).decode("utf-8").splitlines()
    return {path for path in tracked + untracked if path}


def validate_release_boundary() -> None:
    for path in changed_paths():
        allowed = path in ALLOWED_CHANGED_FILES or path.startswith(ALLOWED_CHANGED_PREFIXES)
        check(allowed, f"Phase 6 framework crossed its owned-file boundary: {path}")


def scan_no_raw_state(root: Path = EVAL) -> None:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        check(not path.is_symlink(), f"Phase 6 tree contains a symlink: {path}")
        name = path.name.casefold()
        check(name not in FORBIDDEN_PHASE6_FILENAMES, f"raw V0/archive artifact is prohibited: {path}")
        check(not name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".age")), f"raw V0/archive extension is prohibited: {path}")
        with path.open("rb") as handle:
            prefix = handle.read(64)
        check(not prefix.startswith(b"SQLite format 3\x00"), f"tracked SQLite content is prohibited: {path}")
        check(not prefix.startswith(b"age-encryption.org/v1"), f"tracked encrypted archive content is prohibited: {path}")


def intervention_totals(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_card: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"event_count": 0, "minutes": 0})
    by_taxonomy: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"event_count": 0, "minutes": 0})
    for event in events:
        for bucket, key in [(by_card, event["card_id"]), (by_taxonomy, event["taxonomy"])]:
            bucket[key]["event_count"] += 1
            bucket[key]["minutes"] += event["minutes"]
    return {
        "event_count": len(events),
        "minutes": sum(event["minutes"] for event in events),
        "by_card": [
            {"card_id": key, **value} for key, value in sorted(by_card.items())
        ],
        "by_taxonomy": [
            {"taxonomy": key, **value}
            for key, value in sorted(by_taxonomy.items())
        ],
    }


def validate_lane(document: dict[str, Any]) -> list[str]:
    validate(document, schema("lane-assignment"), "lane assignment")
    expected = ALL_CARDS if document["lane"] == "cold-clone" else WARM_CARDS
    exact_cards(document["cards"], expected, "lane assignment")
    if document["lane"] == "cold-clone":
        check(document["warm_capture"] is None, "cold lane cannot bind warm capture")
        check(document["baseline"]["kind"] == "phase5-cold-baseline", "cold lane must bind Phase 5 baseline")
    else:
        check(document["warm_capture"] is not None, "warm lane requires external capture identity")
        check(document["baseline"]["kind"] == "warm-v0-supplement", "warm lane must bind warm supplement")
    check(document["assignment_sha256"] == canonical_digest(document, "assignment_sha256"), "lane assignment digest mismatch")
    return expected


def validate_condition(document: dict[str, Any], lane: dict[str, Any], artifact_digests: dict[str, str]) -> None:
    validate(document, schema("condition-lock"), "condition lock")
    check(document["condition_identity_sha256"] == canonical_digest(document, "condition_identity_sha256"), "condition identity digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "condition/lane identity mismatch")
    check(document["starting_revision"] == lane["starting_revision"] and document["starting_tree"] == lane["starting_tree"], "condition changed starting identity")
    capture_sha = None if lane["warm_capture"] is None else lane["warm_capture"]["sha256"]
    check(document["warm_capture_sha256"] == capture_sha, "condition warm-capture identity mismatch")
    expected = lane["cards"]
    exact_cards(document["prompts"], expected, "condition prompts")
    exact_cards(document["acceptance_commands"], expected, "condition acceptance commands")
    tool_names = [tool["name"] for tool in document["tools"]]
    check(len(tool_names) == len(set(tool_names)), "condition tool names are not unique")
    check(set(document["enabled_tools"]) <= set(tool_names), "condition enables undeclared tool")
    check(len(document["enabled_tools"]) == len(set(document["enabled_tools"])), "condition repeats enabled tool")
    for prompt in document["prompts"]:
        check(artifact_digests.get(prompt["artifact"]) == prompt["sha256"], f"prompt is outside authenticated packet: {prompt['artifact']}")
    for command in document["acceptance_commands"]:
        check(command["argv"][0] in document["enabled_tools"], f"{command['card_id']} acceptance executable is not enabled")
    limits = {item["card_id"]: item["seconds"] for item in document["time_limits"]}
    if lane["lane"] == "cold-clone":
        exact_cards(document["time_limits"], ["P3", "P6"], "condition time limits")
        check(limits == {"P3": 300, "P6": 300}, "cold lane must preserve exact P3/P6 five-minute limits")
    else:
        check(not limits, "warm P0/P1 lane cannot invent fresh-agent time limits")


def validate_cold_condition_against_phase5(
    document: dict[str, Any], lane: dict[str, Any]
) -> None:
    packet = ROOT / "tests/evals/v1-phase5/evidence" / lane["pilot_id"]
    environment = load_json(packet / "environment.json")
    baseline = load_json(packet / "baseline-result.json")
    check(document["card_catalog_sha256"] == baseline["card_set_sha256"], "cold condition changed Phase 5 card catalog")
    check(document["starting_revision"] == baseline["starting_revision"], "cold condition changed Phase 5 starting revision")
    for field in [
        "model",
        "reasoning",
        "operating_system",
        "architecture",
        "tools",
        "enabled_tools",
        "permissions",
        "evaluator_id",
        "acceptance_commands",
    ]:
        check(document[field] == environment[field], f"cold condition changed Phase 5 {field}")


def validate_subject(document: dict[str, Any], lane: dict[str, Any], artifact_digests: dict[str, str]) -> None:
    validate(document, schema("candidate-subject"), "evaluation subject")
    check(document["subject_identity_sha256"] == canonical_digest(document, "subject_identity_sha256"), "subject identity digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "subject/lane identity mismatch")
    roles = [artifact["role"] for artifact in document["artifacts"]]
    paths = [artifact["path"] for artifact in document["artifacts"]]
    check(len(paths) == len(set(paths)), "subject contains duplicate artifact paths")
    for artifact in document["artifacts"]:
        check(artifact_digests.get(artifact["path"]) == artifact["sha256"], f"subject artifact is outside authenticated packet: {artifact['path']}")
    if document["kind"] == "candidate":
        required = {"core-binary", "evaluation-payload-index", "template-set", "pilot-candidate-bundle", "capability-asset"}
        check(required <= set(roles), f"candidate subject lacks required roles: {sorted(required - set(roles))}")
        if lane["lane"] == "warm-v0-copy":
            check("bridge-binary" in roles, "warm candidate subject lacks bridge identity")
        capability_artifacts = {artifact["path"] for artifact in document["artifacts"] if artifact["role"] == "capability-asset"}
        check(set(document["capability_paths"]) == capability_artifacts, "candidate capability path set is incomplete")


def validate_interventions(document: dict[str, Any], lane: dict[str, Any]) -> None:
    validate(document, schema("intervention-log"), "intervention log")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "intervention/lane identity mismatch")
    check(document["totals"] == intervention_totals(document["events"]), "intervention totals are incomplete")
    check(all(event["card_id"] in lane["cards"] for event in document["events"]), "intervention cites card outside lane")
    check(document["intervention_log_sha256"] == canonical_digest(document, "intervention_log_sha256"), "intervention log digest mismatch")


def validate_hint_leakage(
    result: dict[str, Any], subject: dict[str, Any], packet: Path, artifact_visibility: dict[str, str]
) -> None:
    cards = {record["card_id"]: record for record in result["cards"]}
    for card_id in ("P3", "P6"):
        held_out = cards[card_id]["held_out"]
        check(held_out is not None, f"{card_id} candidate lacks fresh-agent visibility record")
        check(set(held_out["visible_paths"]).isdisjoint(held_out["evaluator_only_paths"]), f"{card_id} agent/evaluator visibility overlaps")
        check(all(not path.startswith("tests/evals/") and "/evidence/" not in path for path in held_out["visible_paths"]), f"{card_id} exposed evaluator evidence to fresh agent")
        prompt_path = contained_member(packet, held_out["prompt_artifact"], f"{card_id} held-out prompt")
        check(artifact_visibility.get(held_out["prompt_artifact"]) == "evaluator-only", f"{card_id} prompt custody is not evaluator-only")
        prompt = prompt_path.read_text(encoding="utf-8").casefold()
        for capability in subject["capability_paths"]:
            check(capability.casefold() not in prompt, f"{card_id} prompt leaks capability path")
        for path in held_out["evaluator_only_paths"]:
            check(path.casefold() not in prompt, f"{card_id} prompt leaks evaluator-only evidence path")
        check("original correction" not in prompt and "repair is" not in prompt, f"{card_id} prompt leaks correction content")


def validate_result(
    document: dict[str, Any], lane: dict[str, Any], condition: dict[str, Any],
    subject: dict[str, Any], interventions: dict[str, Any], artifact_digests: dict[str, str],
) -> None:
    validate(document, schema("candidate-result"), "Phase 6 result")
    check(document["result_sha256"] == canonical_digest(document, "result_sha256"), "result digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "result/lane identity mismatch")
    check(document["condition_identity_sha256"] == condition["condition_identity_sha256"], "result condition identity mismatch")
    check(document["subject_identity_sha256"] == subject["subject_identity_sha256"], "result subject identity mismatch")
    exact_cards(document["cards"], lane["cards"], "Phase 6 result")
    check(document["intervention_log_sha256"] == interventions["intervention_log_sha256"], "result intervention identity mismatch")
    check(artifact_digests.get(document["intervention_log"]) == sha256_file(Path(interventions["_path"])), "result intervention artifact digest mismatch")
    started = parse_time(document["started_at"], "result.started_at")
    completed = parse_time(document["completed_at"], "result.completed_at")
    check(started <= completed, "result completes before it starts")
    for event in interventions["events"]:
        timestamp = parse_time(event["timestamp"], "intervention.timestamp")
        check(started <= timestamp <= completed, "intervention falls outside result interval")
    for card in document["cards"]:
        commands = {
            item["card_id"]: json.dumps(
                {"argv": item["argv"]}, sort_keys=True, separators=(",", ":")
            )
            for item in condition["acceptance_commands"]
        }
        for evidence in card["evidence"]:
            check(evidence in artifact_digests, f"{card['card_id']} evidence is outside packet custody")
        if card["outcome"] == "inapplicable":
            check(card["card_id"] == "P1" and card["finding"].strip(), "only P1 may be inapplicable with a finding")
            check(card["acceptance_command"] == "inapplicable", "inapplicable P1 has executable acceptance command")
        else:
            check(not card["finding"], f"{card['card_id']} contains contradictory finding")
            check(card["acceptance_command"] == commands[card["card_id"]], f"{card['card_id']} result changed locked acceptance argv")
        if document["run_kind"] == "candidate":
            check(card["outcome"] in {"passed", "inapplicable"}, f"candidate acceptance failed: {card['card_id']}")
    validate_negative_conditions(document["negative_conditions"])


def validate_negative_conditions(records: list[dict[str, Any]]) -> None:
    checks = {item["condition"]: item for item in records}
    check(set(checks) == MANDATORY_NEGATIVES, "mandatory negative-condition set is incomplete")
    check(all(item["outcome"] == "clear" for item in checks.values()), "candidate has a failed mandatory negative condition")


def validate_comparison(document: dict[str, Any], lane: dict[str, Any], condition: dict[str, Any], subject: dict[str, Any]) -> None:
    validate(document, schema("comparison-report"), "comparison report")
    check(document["comparison_sha256"] == canonical_digest(document, "comparison_sha256"), "comparison digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "comparison/lane identity mismatch")
    check(document["baseline_condition_identity_sha256"] == document["candidate_condition_identity_sha256"] == condition["condition_identity_sha256"], "baseline/candidate conditions are not identical")
    check(document["candidate_subject_identity_sha256"] == subject["subject_identity_sha256"], "comparison candidate subject mismatch")
    if lane["lane"] == "cold-clone":
        phase5 = load_json(
            ROOT
            / "tests/evals/v1-phase5/evidence"
            / lane["pilot_id"]
            / "baseline-result.json"
        )
        check(
            document["baseline_subject_identity_sha256"]
            == phase5["evaluation_subject"]["sha256"],
            "comparison baseline subject differs from authenticated Phase 5 subject",
        )
    exact_cards(document["cards"], lane["cards"], "comparison report")
    for card in document["cards"]:
        check(not (card["baseline_outcome"] == "passed" and card["candidate_outcome"] != "passed"), f"functional regression on {card['card_id']}")
        check(card["candidate_outcome"] in {"passed", "inapplicable"}, f"candidate comparison failed on {card['card_id']}")
    check(set(document["improvement"]["cards"]) <= set(lane["cards"]), "comparison improvement cites card outside lane")


def validate_manifest(packet: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    manifest = load_json(contained_member(packet, "packet-manifest.json", "packet manifest"))
    validate(manifest, schema("packet-manifest"), "packet manifest")
    paths = [entry["path"] for entry in manifest["artifacts"]]
    check(len(paths) == len(set(paths)), "packet manifest contains duplicate paths")
    required = {"lane-assignment.json", "condition.json", "subject.json", "interventions.json", "result.json"}
    check(required <= set(paths), f"packet omits core records: {sorted(required - set(paths))}")
    digests: dict[str, str] = {}
    visibility: dict[str, str] = {}
    for entry in manifest["artifacts"]:
        path = contained_member(packet, entry["path"], "packet artifact")
        digest = sha256_file(path)
        check(digest == entry["sha256"], f"packet artifact digest mismatch: {entry['path']}")
        digests[entry["path"]] = digest
        visibility[entry["path"]] = entry["visibility"]
        lower = entry["path"].casefold()
        check(not any(name in lower for name in FORBIDDEN_PHASE6_FILENAMES), f"packet manifest attempts raw V0/archive custody: {entry['path']}")
    actual = {
        path.relative_to(packet).as_posix()
        for path in packet.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    expected = set(paths) | {"packet-manifest.json", "authentication.json"}
    check(actual == expected, f"packet inventory differs from manifest: missing={sorted(expected-actual)} unlisted={sorted(actual-expected)}")
    return manifest, digests, visibility


def load_external_trust(path: Path | None, expected_sha256: str | None) -> dict[str, dict[str, Any]]:
    check(path is not None and expected_sha256 is not None, "complete Phase 6 evidence requires external trust registry and digest")
    check(path.is_absolute() and path.is_file() and not path.is_symlink(), "external trust registry path is unsafe")
    check(not path.resolve().is_relative_to(ROOT.resolve()), "external trust registry cannot be inside candidate repository")
    check(re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None, "external trust digest is malformed")
    check(sha256_file(path) == expected_sha256, "external trust registry digest mismatch")
    document = load_json(path)
    validate(document, load_json(ROOT / "tests/evals/v1-phase5/schemas/trusted-owners.schema.json"), "external trusted owners")
    owners = {owner["owner_id"]: owner for owner in document["owners"]}
    check(len(owners) == len(document["owners"]), "external trust registry contains duplicate owner IDs")
    return owners


def verify_authentication(
    packet: Path, authentication: dict[str, Any], manifest: dict[str, Any],
    lane: dict[str, Any], condition: dict[str, Any], subject: dict[str, Any],
    result: dict[str, Any], comparison: dict[str, Any] | None, owners: dict[str, dict[str, Any]],
) -> None:
    validate(authentication, schema("signature"), "packet authentication")
    owner_id = authentication["owner_id"]
    check(owner_id == lane["owner_id"] and owner_id in owners, "packet owner is not externally trusted for lane")
    owner = owners[owner_id]
    check(owner["canonical_repository"] == lane["canonical_repository"], "external owner repository differs from lane")
    statement = authentication["statement"]
    check(statement["packet_id"] == manifest["packet_id"], "authentication packet ID mismatch")
    check(statement["pilot_id"] == lane["pilot_id"] and statement["lane_id"] == lane["lane_id"], "authentication lane identity mismatch")
    check(statement["canonical_repository"] == lane["canonical_repository"], "authentication repository mismatch")
    check(statement["packet_manifest_sha256"] == sha256_file(packet / "packet-manifest.json"), "authentication manifest digest mismatch")
    check(statement["condition_identity_sha256"] == condition["condition_identity_sha256"], "authentication condition mismatch")
    check(statement["subject_identity_sha256"] == subject["subject_identity_sha256"], "authentication subject mismatch")
    check(statement["result_sha256"] == result["result_sha256"], "authentication result mismatch")
    expected_comparison = None if comparison is None else comparison["comparison_sha256"]
    check(statement["comparison_sha256"] == expected_comparison, "authentication comparison mismatch")
    check(statement["completed_at"] == result["completed_at"], "authentication completion mismatch")
    check(parse_time(statement["completed_at"], "statement.completed_at") <= parse_time(statement["published_at"], "statement.published_at"), "authenticated result published before completion")
    with tempfile.TemporaryDirectory(prefix="phase6-signature-") as temporary:
        root = Path(temporary)
        allowed = root / "allowed_signers"
        signature = root / "statement.sig"
        allowed.write_text(f"{owner_id} {owner['public_key']}\n", encoding="utf-8")
        signature.write_text(authentication["signature"], encoding="utf-8")
        run(
            ["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", owner_id, "-n", NAMESPACE, "-s", str(signature)],
            input_bytes=canonical_bytes(statement),
        )


def validate_packet(packet: Path, owners: dict[str, dict[str, Any]]) -> dict[str, Any]:
    manifest, digests, visibility = validate_manifest(packet)
    lane = load_json(contained_member(packet, "lane-assignment.json", "lane assignment"))
    validate_lane(lane)
    check(manifest["pilot_id"] == lane["pilot_id"] and manifest["lane_id"] == lane["lane_id"], "manifest/lane identity mismatch")
    check(digests.get(lane["baseline"]["artifact"]) == lane["baseline"]["sha256"], "lane baseline artifact is outside authenticated packet")
    if lane["warm_capture"] is not None:
        capture_path = contained_member(packet, lane["warm_capture"]["artifact"], "warm capture")
        check(digests.get(lane["warm_capture"]["artifact"]) == lane["warm_capture"]["sha256"], "lane warm capture is outside authenticated packet")
        capture = load_json(capture_path)
        validate(capture, schema("warm-v0-capture"), "warm capture")
        check(capture["capture_sha256"] == canonical_digest(capture, "capture_sha256"), "warm capture self-digest mismatch")
        check(capture["pilot_id"] == lane["pilot_id"] and capture["canonical_repository"] == lane["canonical_repository"], "warm capture owner scope differs from lane")
        check(capture["starting_revision"] == lane["starting_revision"] and capture["starting_tree"] == lane["starting_tree"], "warm capture starting identity differs from lane")
    condition = load_json(contained_member(packet, "condition.json", "condition"))
    subject = load_json(contained_member(packet, "subject.json", "subject"))
    interventions = load_json(contained_member(packet, "interventions.json", "interventions"))
    interventions["_path"] = str(packet / "interventions.json")
    result = load_json(contained_member(packet, "result.json", "result"))
    comparison = None
    if "comparison.json" in digests:
        comparison = load_json(contained_member(packet, "comparison.json", "comparison"))
    validate_condition(condition, lane, digests)
    if lane["lane"] == "cold-clone":
        validate_cold_condition_against_phase5(condition, lane)
    validate_subject(subject, lane, digests)
    validate_interventions({key: value for key, value in interventions.items() if key != "_path"}, lane)
    validate_result(result, lane, condition, subject, interventions, digests)
    if result["run_kind"] == "candidate":
        check(comparison is not None, "candidate packet lacks baseline comparison")
        validate_comparison(comparison, lane, condition, subject)
    else:
        check(lane["lane"] == "warm-v0-copy", "only warm lane may publish supplemental baseline")
        check(comparison is None, "pre-disclosure warm baseline cannot contain candidate comparison")
    if result["run_kind"] == "candidate" and lane["lane"] == "cold-clone":
        validate_hint_leakage(result, subject, packet, visibility)
    authentication = load_json(contained_member(packet, "authentication.json", "authentication"))
    verify_authentication(packet, authentication, manifest, lane, condition, subject, result, comparison, owners)
    return {
        "pilot_id": lane["pilot_id"],
        "lane_id": lane["lane_id"],
        "lane": lane["lane"],
        "run_kind": result["run_kind"],
        "condition_identity_sha256": condition["condition_identity_sha256"],
        "subject_identity_sha256": subject["subject_identity_sha256"],
        "comparison_baseline_subject_identity_sha256": (
            None
            if comparison is None
            else comparison["baseline_subject_identity_sha256"]
        ),
        "improvement": None if comparison is None else comparison["improvement"],
    }


def validate_index(
    *, require_complete: bool, trusted_registry: Path | None, trusted_sha256: str | None
) -> None:
    index = load_json(EVIDENCE / "index.json")
    validate(index, schema("evidence-index"), "Phase 6 evidence index")
    pilot_ids = [pilot["pilot_id"] for pilot in index["pilots"]]
    check(len(pilot_ids) == len(set(pilot_ids)), "Phase 6 index repeats pilot ID")
    lane_pairs = [(pilot["pilot_id"], lane) for pilot in index["pilots"] for lane in pilot["lanes"]]
    check(len(lane_pairs) == len(set(lane_pairs)), "Phase 6 index repeats pilot lane")
    if index["status"] == "candidate-results-pending":
        check(index["blockers"], "pending Phase 6 index hides blockers")
        check(all(not pilot["packets"] and pilot["status"] != "complete" for pilot in index["pilots"]), "pending Phase 6 index exposes candidate packets or completion")
        actual = {path.name for path in EVIDENCE.iterdir()}
        check(actual == {"index.json"}, "pending Phase 6 index must not contain undisclosed packet directories")
        if require_complete:
            raise PendingEvidence("candidate results are pending")
        print("Phase 6 candidate evidence pending: framework is valid; no acceptance claimed")
        return
    check(not index["blockers"], "complete Phase 6 index retains blockers")
    check(all(pilot["status"] == "complete" and pilot["packets"] for pilot in index["pilots"]), "complete Phase 6 index has incomplete pilot")
    owners = load_external_trust(trusted_registry, trusted_sha256)
    packets: list[dict[str, Any]] = []
    named_paths: set[str] = set()
    for pilot in index["pilots"]:
        for relative in pilot["packets"]:
            check(relative not in named_paths, "Phase 6 index repeats packet path")
            named_paths.add(relative)
            packet = EVIDENCE.joinpath(*relative_name(relative, "packet path").parts)
            check(packet.is_dir() and not packet.is_symlink() and packet.resolve().is_relative_to(EVIDENCE.resolve()), "Phase 6 packet directory is unsafe")
            record = validate_packet(packet, owners)
            check(record["pilot_id"] == pilot["pilot_id"] and record["lane"] in pilot["lanes"], "packet is outside indexed pilot lane")
            packets.append(record)
    for pilot in index["pilots"]:
        for lane in pilot["lanes"]:
            relevant = [packet for packet in packets if packet["pilot_id"] == pilot["pilot_id"] and packet["lane"] == lane]
            kinds = {packet["run_kind"] for packet in relevant}
            required = {"candidate"} if lane == "cold-clone" else {"warm-baseline", "candidate"}
            check(required <= kinds, f"complete index lacks required {pilot['pilot_id']} {lane} packets")
            if lane == "warm-v0-copy":
                baselines = [packet for packet in relevant if packet["run_kind"] == "warm-baseline"]
                candidates = [packet for packet in relevant if packet["run_kind"] == "candidate"]
                check(len(baselines) == 1 and len(candidates) == 1, f"warm lane requires exactly one baseline and candidate packet for {pilot['pilot_id']}")
                baseline = baselines[0]
                candidate = candidates[0]
                check(baseline["condition_identity_sha256"] == candidate["condition_identity_sha256"], "warm baseline/candidate condition identity differs")
                check(candidate["comparison_baseline_subject_identity_sha256"] == baseline["subject_identity_sha256"], "warm candidate comparison does not bind signed warm baseline subject")
    check(any(packet["improvement"] and packet["improvement"]["cards"] for packet in packets if packet["run_kind"] == "candidate"), "complete Phase 6 evidence lacks concrete improvement")


class PendingEvidence(VerificationError):
    pass


def expect_rejection(label: str, function: Callable[[], None]) -> None:
    try:
        function()
    except VerificationError:
        return
    raise VerificationError(f"negative fixture was accepted: {label}")


def self_test_contracts() -> None:
    digest64 = "a" * 64
    commit40 = "b" * 40
    cold = {
        "schema": "repository-harness-phase6-lane-assignment/v1",
        "pilot_id": "synthetic-pilot",
        "owner_id": "synthetic-owner",
        "canonical_repository": "https://example.com/owner/repository.git",
        "lane_id": "synthetic-cold-lane",
        "lane": "cold-clone",
        "starting_revision": commit40,
        "starting_tree": "c" * 40,
        "baseline": {"kind": "phase5-cold-baseline", "identity": "baseline", "artifact": "baseline.json", "sha256": digest64},
        "warm_capture": None,
        "cards": ALL_CARDS,
        "assignment_sha256": "",
    }
    cold["assignment_sha256"] = canonical_digest(cold, "assignment_sha256")
    validate_lane(cold)
    warm = dict(cold)
    warm.update(
        {
            "lane_id": "synthetic-warm-lane",
            "lane": "warm-v0-copy",
            "baseline": {"kind": "warm-v0-supplement", "identity": "warm", "artifact": "warm.json", "sha256": digest64},
            "warm_capture": {"artifact": "capture.json", "sha256": "d" * 64},
            "cards": WARM_CARDS,
            "assignment_sha256": "",
        }
    )
    warm["assignment_sha256"] = canonical_digest(warm, "assignment_sha256")
    validate_lane(warm)
    unknown = dict(cold)
    unknown["pilot_fix"] = True
    expect_rejection("unknown lane field", lambda: validate_lane(unknown))
    mixed = dict(cold)
    mixed["warm_capture"] = {"artifact": "capture.json", "sha256": digest64}
    mixed["assignment_sha256"] = canonical_digest(mixed, "assignment_sha256")
    expect_rejection("warm capture in cold lane", lambda: validate_lane(mixed))
    missing = dict(cold)
    missing["cards"] = ALL_CARDS[:-1]
    missing["assignment_sha256"] = canonical_digest(missing, "assignment_sha256")
    expect_rejection("omitted P7", lambda: validate_lane(missing))

    events = [
        {
            "card_id": "P6",
            "actor": "synthetic-evaluator",
            "timestamp": "2000-01-01T00:01:00Z",
            "taxonomy": "correction",
            "reason": "synthetic event",
            "minutes": 2,
            "changed_outcome": True,
        }
    ]
    log = {
        "schema": "repository-harness-phase6-intervention-log/v1",
        "pilot_id": cold["pilot_id"],
        "lane_id": cold["lane_id"],
        "run_kind": "candidate",
        "events": events,
        "totals": intervention_totals(events),
        "intervention_log_sha256": "",
    }
    log["intervention_log_sha256"] = canonical_digest(log, "intervention_log_sha256")
    validate_interventions(log, cold)
    bad_totals = json.loads(json.dumps(log))
    bad_totals["totals"]["minutes"] = 1
    expect_rejection("incomplete intervention totals", lambda: validate_interventions(bad_totals, cold))

    negative_checks = [
        {"condition": condition, "outcome": "clear", "evidence": "synthetic proof"}
        for condition in sorted(MANDATORY_NEGATIVES)
    ]
    validate_negative_conditions(negative_checks)
    missing_negative = negative_checks[:-1]
    expect_rejection(
        "missing mandatory negative condition",
        lambda: validate_negative_conditions(missing_negative),
    )
    failed_negative = json.loads(json.dumps(negative_checks))
    failed_negative[0]["outcome"] = "failed"
    expect_rejection(
        "failed mandatory negative condition",
        lambda: validate_negative_conditions(failed_negative),
    )

    comparison_lane = dict(cold)
    comparison_lane["pilot_id"] = "harness-benchmark-phase5-pilot"
    comparison = {
        "schema": "repository-harness-phase6-comparison/v1",
        "pilot_id": comparison_lane["pilot_id"],
        "lane_id": comparison_lane["lane_id"],
        "baseline_condition_identity_sha256": digest64,
        "candidate_condition_identity_sha256": digest64,
        "baseline_subject_identity_sha256": "8bf677d9c40e50ea02da38322b4a21fe59bd94f55d77ab417b7ea31a73a090a3",
        "candidate_subject_identity_sha256": "f" * 64,
        "cards": [{"card_id": card, "baseline_outcome": "failed" if card == "P6" else "passed", "candidate_outcome": "passed"} for card in ALL_CARDS],
        "no_functional_regression": True,
        "improvement": {"kind": "outcome", "cards": ["P6"], "evidence": "synthetic failed-to-passed comparison"},
        "comparison_sha256": "",
    }
    comparison["comparison_sha256"] = canonical_digest(comparison, "comparison_sha256")
    condition = {"condition_identity_sha256": digest64}
    subject = {"subject_identity_sha256": "f" * 64}
    validate_comparison(comparison, comparison_lane, condition, subject)
    drift = json.loads(json.dumps(comparison))
    drift["candidate_condition_identity_sha256"] = "0" * 64
    drift["comparison_sha256"] = canonical_digest(drift, "comparison_sha256")
    expect_rejection("condition drift", lambda: validate_comparison(drift, comparison_lane, condition, subject))
    regression = json.loads(json.dumps(comparison))
    regression["cards"][0]["baseline_outcome"] = "passed"
    regression["cards"][0]["candidate_outcome"] = "failed"
    regression["comparison_sha256"] = canonical_digest(regression, "comparison_sha256")
    expect_rejection("functional regression", lambda: validate_comparison(regression, comparison_lane, condition, subject))

    with tempfile.TemporaryDirectory(prefix="phase6-negative-") as temporary:
        root = Path(temporary)
        (root / "harness.db").write_bytes(b"SQLite format 3\x00synthetic")
        expect_rejection("tracked raw database", lambda: scan_no_raw_state(root))

    with tempfile.TemporaryDirectory(prefix="phase6-hint-") as temporary:
        packet = Path(temporary)
        prompt = packet / "p6-prompt.md"
        prompt.write_text(
            "Diagnose the comparable failure using normal repository instructions.\n",
            encoding="utf-8",
        )
        held_out = {
            "prompt_artifact": "p6-prompt.md",
            "visible_paths": ["AGENTS.md"],
            "evaluator_only_paths": ["evaluation/repeated-correction.md"],
            "discovery_path": ["AGENTS.md", "target feedback"],
            "time_limit_seconds": 300,
            "completed_seconds": 120,
        }
        hint_result = {
            "cards": [
                {"card_id": "P3", "held_out": held_out},
                {"card_id": "P6", "held_out": held_out},
            ]
        }
        hint_subject = {"capability_paths": ["docs/capabilities/native-check.md"]}
        visibility = {"p6-prompt.md": "evaluator-only"}
        validate_hint_leakage(hint_result, hint_subject, packet, visibility)
        prompt.write_text(
            "Use docs/capabilities/native-check.md to make the repair.\n",
            encoding="utf-8",
        )
        expect_rejection(
            "held-out capability-path leakage",
            lambda: validate_hint_leakage(
                hint_result, hint_subject, packet, visibility
            ),
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--framework-only", action="store_true")
    modes.add_argument("--require-candidate-results", action="store_true")
    parser.add_argument("--trusted-owner-registry")
    parser.add_argument("--trusted-owner-registry-sha256")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        lock: dict[str, Any] = {}
        proof("closed schemas and exact Phase 5 baseline lock", lambda: lock.update(validate_baseline_lock()))
        proof("Phase 5 worktree immutability", lambda: verify_phase5_immutability(lock))
        proof("cold/warm, identity, totals, regression, and raw-state negatives", self_test_contracts)
        proof("owned-file and release boundary", validate_release_boundary)
        proof("no raw V0 database or archive in Phase 6 custody", scan_no_raw_state)
        registry = Path(arguments.trusted_owner_registry) if arguments.trusted_owner_registry else None
        proof(
            "honest evidence index state",
            lambda: validate_index(
                require_complete=arguments.require_candidate_results,
                trusted_registry=registry,
                trusted_sha256=arguments.trusted_owner_registry_sha256,
            ),
        )
    except PendingEvidence as error:
        print(f"Phase 6 candidate evidence pending: {error}", file=sys.stderr)
        return 2
    except VerificationError as error:
        print(f"Phase 6 verification failed: {error}", file=sys.stderr)
        return 1
    print("Phase 6 framework verification passed; candidate evidence remains pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

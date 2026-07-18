#!/usr/bin/env python3
"""Deterministic Phase 5 dogfood and external-pilot evidence contracts."""

from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "tests" / "evals" / "v1-phase5"
SCHEMAS = EVAL / "schemas"
CARDS = {f"P{number}" for number in range(8)}
CORE_CALL = re.compile(
    r"(?:^|[\s;&|])(?:[^\s;&|]*/)?harness(?:\.exe)?\s+(?:install|update|audit|scaffold|status|version)(?:\s|$)"
)
CORE_VERSION_CALL = re.compile(r"(?:^|[\s;&|])(?:[^\s;&|]*/)?harness(?:\.exe)?\s+--version(?:\s|$)")


class VerificationError(RuntimeError):
    pass


PASS_COUNT = 0


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def proof(label: str, function: Callable[[], None]) -> None:
    global PASS_COUNT
    function()
    PASS_COUNT += 1
    print(f"ok {PASS_COUNT:02d} - {label}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read JSON {path.relative_to(ROOT)}: {error}") from error


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_digest(document: dict[str, Any], omitted: str) -> str:
    payload = {key: value for key, value in document.items() if key != omitted}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256_bytes(encoded)


def schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMAS / f"{name}.schema.json")


def validate(instance: Any, contract: dict[str, Any], location: str = "$") -> None:
    expected_type = contract.get("type")
    matches = {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
        "boolean": isinstance(instance, bool),
    }
    if expected_type is not None:
        check(matches.get(expected_type, False), f"{location}: expected {expected_type}")
    if "const" in contract:
        check(instance == contract["const"], f"{location}: expected constant {contract['const']!r}")
    if "enum" in contract:
        check(instance in contract["enum"], f"{location}: value is outside the closed enum")

    if isinstance(instance, dict):
        required = contract.get("required", [])
        missing = sorted(set(required) - set(instance))
        check(not missing, f"{location}: missing required fields {missing}")
        properties = contract.get("properties", {})
        if contract.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            check(not extra, f"{location}: unexpected fields {extra}")
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], f"{location}.{key}")
    elif isinstance(instance, list):
        check(len(instance) >= contract.get("minItems", 0), f"{location}: too few items")
        if contract.get("uniqueItems"):
            frozen = [json.dumps(item, sort_keys=True) for item in instance]
            check(len(frozen) == len(set(frozen)), f"{location}: duplicate items")
        if "items" in contract:
            for index, value in enumerate(instance):
                validate(value, contract["items"], f"{location}[{index}]")
    elif isinstance(instance, str):
        check(len(instance) >= contract.get("minLength", 0), f"{location}: string is too short")
        if "pattern" in contract:
            check(re.fullmatch(contract["pattern"], instance) is not None, f"{location}: string does not match pattern")
    elif isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in contract:
            check(instance >= contract["minimum"], f"{location}: integer is below minimum")


def exact_cards(records: list[dict[str, Any]], location: str) -> None:
    ids = [record.get("card_id") for record in records]
    check(set(ids) == CARDS and len(ids) == 8, f"{location}: expected exactly P0-P7, found {ids}")


def validate_catalog() -> str:
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        contract = load_json(path)
        check(contract.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"schema draft changed: {path.name}")
        check(contract.get("type") == "object", f"top-level schema is not an object: {path.name}")
    catalog_path = EVAL / "cards" / "catalog.json"
    catalog = load_json(catalog_path)
    check(catalog.get("schema") == "repository-harness-pilot-card-catalog/v1", "card catalog schema identity changed")
    check(catalog.get("catalog_revision") == 1, "card catalog revision changed without a new contract")
    exact_cards(catalog.get("cards", []), "card catalog")
    for entry in catalog["cards"]:
        path = EVAL / entry["path"]
        check(path.parent == EVAL / "cards" and path.is_file(), f"card path is missing or escaped: {entry['path']}")
        check(sha256_file(path) == entry["sha256"], f"card digest changed: {entry['card_id']}")
        card = load_json(path)
        validate(card, schema("card"), f"card {entry['card_id']}")
        check(card["card_id"] == entry["card_id"], f"card identity/path mismatch: {entry['card_id']}")
    return sha256_file(catalog_path)


def validate_evidence_index(catalog_digest: str) -> None:
    index = load_json(EVAL / "evidence" / "index.json")
    validate(index, schema("evidence-index"), "evidence index")
    check(index["card_catalog"] == "cards/catalog.json", "evidence index points to another card catalog")
    if index["status"] == "candidate-awaiting-pilot-authorization":
        check(not index["pilots"], "unauthorized candidate index names pilot evidence")
        check(bool(index["blockers"]), "candidate evidence index hides its blockers")
    else:
        check(len(index["pilots"]) >= 2 and not index["blockers"], "complete evidence index is internally contradictory")
    check(catalog_digest == sha256_file(EVAL / index["card_catalog"]), "evidence index card catalog digest changed")


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, check=False,
    )
    check(completed.returncode == 0, f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def reject_path_moves(name_status: str, mapped_paths: set[str]) -> None:
    for line in name_status.splitlines():
        fields = line.split("\t")
        status = fields[0]
        if status.startswith("R"):
            raise VerificationError(f"path move is prohibited: {fields[1]} -> {fields[2]}")
        if status == "D" and len(fields) > 1 and fields[1] in mapped_paths:
            raise VerificationError(f"mapped useful path was deleted: {fields[1]}")


def reject_core_calls(commands: list[dict[str, Any]]) -> None:
    for entry in commands:
        command = entry.get("command", "")
        if CORE_CALL.search(command) or CORE_VERSION_CALL.search(command):
            raise VerificationError(f"ordinary task invoked a V1 core command: {command}")


def execute_ordinary_task(commands: list[dict[str, Any]]) -> None:
    for entry in commands:
        arguments = shlex.split(entry["command"])
        check(arguments and arguments[0] in {"git", "rg"}, f"ordinary task command is outside the fixed native allowlist: {entry['command']}")
        completed = subprocess.run(arguments, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
        check(completed.returncode == entry["exit_code"], f"ordinary task check failed: {entry['command']}\n{completed.stderr}")


def validate_dogfood() -> None:
    mapping = load_json(EVAL / "dogfood" / "repository-map.json")
    validate(mapping, schema("dogfood-map"), "dogfood map")
    dispositions = {
        entry["path"]: entry["disposition"]
        for entry in load_json(ROOT / "release" / "contracts" / "v1" / "path-dispositions.json")["entries"]
    }
    source = mapping["source_revision"]
    check(git("cat-file", "-t", source) == "commit", "dogfood source revision is missing or changed")
    paths = [role["path"] for role in mapping["roles"]]
    check(len(paths) == len(set(paths)), "dogfood map duplicates a useful path")
    for role in mapping["roles"]:
        path = role["path"]
        check(dispositions.get(path) == "target-owned-destination", f"dogfood role violates the accepted Phase 1 path disposition: {path}")
        check((ROOT / path).is_file(), f"mapped useful path is absent: {path}")
        check(git("rev-parse", f"{source}:{path}") == role["source_blob"], f"source blob changed for {path}")
        payload = subprocess.run(["git", "show", f"{source}:{path}"], cwd=ROOT, capture_output=True, check=False).stdout
        check(sha256_bytes(payload) == role["source_sha256"], f"source bytes changed for {path}")
    reject_path_moves(git("diff", "--name-status", source, "--"), set(paths))

    task = load_json(EVAL / "dogfood" / "ordinary-task.json")
    validate(task, schema("ordinary-task"), "ordinary task")
    check(task["starting_revision"] == source, "ordinary task revision does not match the dogfood lock")
    reject_core_calls(task["commands"])
    check(task["core_command_count"] == 0, "ordinary task core-command count is not zero")
    execute_ordinary_task(task["commands"])


def validate_eligibility(document: dict[str, Any]) -> None:
    validate(document, schema("eligibility"), "eligibility")
    exact_cards(document["cards"], "eligibility")
    for card in document["cards"]:
        if card["disposition"] == "inapplicable":
            check(bool(card["finding"].strip()), f"{card['card_id']} is inapplicable without a written evaluator finding")


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
        "by_card": dict(sorted(by_card.items())),
        "by_taxonomy": dict(sorted(by_taxonomy.items())),
    }


def validate_interventions(document: dict[str, Any]) -> None:
    validate(document, schema("intervention-log"), "intervention log")
    check(document["totals"] == intervention_totals(document["events"]), "intervention totals are incomplete or changed")


def validate_environment(document: dict[str, Any]) -> None:
    validate(document, schema("environment-lock"), "environment lock")
    check(document["environment_sha256"] == canonical_digest(document, "environment_sha256"), "environment digest mismatch")
    names = [tool["name"] for tool in document["tools"]]
    check(len(names) == len(set(names)), "environment lock contains duplicate tool identities")


def validate_baseline(document: dict[str, Any]) -> None:
    validate(document, schema("baseline-result"), "baseline result")
    exact_cards(document["cards"], "baseline result")
    check(document["result_sha256"] == canonical_digest(document, "result_sha256"), "baseline result digest mismatch")


def validate_signature(document: dict[str, Any], catalog_digest: str, *, allow_test_only: bool) -> None:
    validate(document, schema("signature"), "owner signature")
    check(document["subject"] == "cards/catalog.json", "owner signature does not name the fixed card catalog")
    check(document["subject_sha256"] == catalog_digest, "signed card-set digest mismatch")
    if not allow_test_only:
        serialized = json.dumps(document, sort_keys=True).lower()
        check("test-only" not in serialized and "synthetic" not in serialized, "test-only signature cannot become live pilot evidence")


def synthetic_packet(catalog_digest: str) -> dict[str, dict[str, Any]]:
    pilot_id = "synthetic-pilot-a"
    enrollment = {
        "schema": "repository-harness-pilot-enrollment/v1", "pilot_id": pilot_id,
        "repository": "test-only://synthetic/repository-a",
        "owner_authorization": {"status": "authorized", "owner": "TEST-ONLY OWNER", "authorized_at": "2000-01-01T00:00:00Z", "scope": "synthetic verifier fixture only", "evidence_ref": "test-only://authority"},
        "starting_revision": {"kind": "git-commit", "value": "1" * 40, "immutable": True},
        "evidence_custody": "test-only://custody", "unrelated_to": ["synthetic-pilot-b"], "card_set_sha256": catalog_digest,
    }
    environment = {
        "schema": "repository-harness-environment-lock/v1", "pilot_id": pilot_id,
        "model": "test-only-model", "reasoning": "test-only", "operating_system": "test-os", "architecture": "test-arch",
        "tools": [{"name": "test-tool", "version": "1"}], "enabled_tools": ["test-tool"], "permissions": ["test-only"],
        "evaluator": "TEST-ONLY EVALUATOR", "fixtures": [], "acceptance_commands": ["test-only-command"], "environment_sha256": "",
    }
    environment["environment_sha256"] = canonical_digest(environment, "environment_sha256")
    eligibility = {
        "schema": "repository-harness-pilot-eligibility/v1", "pilot_id": pilot_id,
        "evaluated_at": "2000-01-01T00:00:00Z", "evaluator": "TEST-ONLY EVALUATOR",
        "cards": [{"card_id": f"P{number}", "disposition": "eligible", "finding": "synthetic eligible fixture"} for number in range(8)],
    }
    interventions = {
        "schema": "repository-harness-intervention-log/v1", "pilot_id": pilot_id, "run_kind": "baseline",
        "events": [{"card_id": "P0", "actor": "TEST-ONLY EVALUATOR", "timestamp": "2000-01-01T00:00:00Z", "taxonomy": "environment/setup", "reason": "exercise totals", "minutes": 2, "changed_outcome": False}],
        "totals": {},
    }
    interventions["totals"] = intervention_totals(interventions["events"])
    signature = {
        "schema": "repository-harness-owner-signature/v1", "subject": "cards/catalog.json", "subject_sha256": catalog_digest,
        "signer": {"name": "TEST-ONLY OWNER", "role": "synthetic fixture", "authority_ref": "test-only://authority"},
        "algorithm": "test-only-not-pilot-evidence", "signed_at": "2000-01-01T00:00:00Z", "signature": "TEST-ONLY-NOT-PILOT-EVIDENCE",
    }
    baseline = {
        "schema": "repository-harness-baseline-result/v1", "pilot_id": pilot_id, "run_kind": "baseline",
        "starting_revision": "1" * 40, "card_set_sha256": catalog_digest, "environment_sha256": environment["environment_sha256"],
        "cards": [{"card_id": f"P{number}", "outcome": "passed", "evidence": ["test-only://evidence"]} for number in range(8)],
        "intervention_log": "interventions.json", "result_sha256": "",
    }
    baseline["result_sha256"] = canonical_digest(baseline, "result_sha256")
    return {"enrollment": enrollment, "environment": environment, "eligibility": eligibility, "interventions": interventions, "signature": signature, "baseline": baseline}


def validate_packet(packet: dict[str, dict[str, Any]], catalog_digest: str, *, allow_test_only: bool = False) -> None:
    validate(packet["enrollment"], schema("pilot-enrollment"), "pilot enrollment")
    validate_environment(packet["environment"])
    validate_eligibility(packet["eligibility"])
    validate_interventions(packet["interventions"])
    validate_signature(packet["signature"], catalog_digest, allow_test_only=allow_test_only)
    validate_baseline(packet["baseline"])
    pilot = packet["enrollment"]["pilot_id"]
    for name in ["environment", "eligibility", "interventions", "baseline"]:
        check(packet[name]["pilot_id"] == pilot, f"{name} belongs to another pilot")
    revision = packet["enrollment"]["starting_revision"]["value"]
    check(packet["baseline"]["starting_revision"] == revision, "baseline starting revision changed after enrollment")
    check(packet["enrollment"]["card_set_sha256"] == catalog_digest == packet["baseline"]["card_set_sha256"], "packet card-set digest mismatch")
    check(packet["baseline"]["environment_sha256"] == packet["environment"]["environment_sha256"], "baseline environment changed after lock")
    authorization = packet["enrollment"]["owner_authorization"]
    signer = packet["signature"]["signer"]
    check(signer["name"] == authorization["owner"], "card-set signer is not the authorizing owner")
    check(signer["authority_ref"] == authorization["evidence_ref"], "signature authority does not match enrollment authorization")
    check(packet["eligibility"]["evaluator"] == packet["environment"]["evaluator"], "eligibility evaluator differs from environment lock")
    dispositions = {entry["card_id"]: entry["disposition"] for entry in packet["eligibility"]["cards"]}
    for result in packet["baseline"]["cards"]:
        if result["outcome"] == "inapplicable":
            check(dispositions[result["card_id"]] == "inapplicable", f"{result['card_id']} result lacks an inapplicability finding")


def expect_rejection(label: str, function: Callable[[], None]) -> None:
    try:
        function()
    except VerificationError:
        return
    raise VerificationError(f"negative fixture was accepted: {label}")


def validate_negative_contracts(catalog_digest: str) -> None:
    base = synthetic_packet(catalog_digest)

    changed_revision = copy.deepcopy(base)
    changed_revision["baseline"]["starting_revision"] = "2" * 40
    changed_revision["baseline"]["result_sha256"] = canonical_digest(changed_revision["baseline"], "result_sha256")
    expect_rejection("changed immutable revision", lambda: validate_packet(changed_revision, catalog_digest, allow_test_only=True))

    unsigned = copy.deepcopy(base)
    unsigned["signature"]["signature"] = ""
    expect_rejection("unsigned card set", lambda: validate_packet(unsigned, catalog_digest, allow_test_only=True))

    digest_mismatch = copy.deepcopy(base)
    digest_mismatch["signature"]["subject_sha256"] = "0" * 64
    expect_rejection("digest-mismatched card set", lambda: validate_packet(digest_mismatch, catalog_digest, allow_test_only=True))

    expect_rejection("test-only signature presented as live evidence", lambda: validate_packet(copy.deepcopy(base), catalog_digest))

    incomplete_environment = copy.deepcopy(base)
    del incomplete_environment["environment"]["permissions"]
    expect_rejection("incomplete environment", lambda: validate_packet(incomplete_environment, catalog_digest, allow_test_only=True))

    omitted_card = copy.deepcopy(base)
    omitted_card["eligibility"]["cards"].pop()
    expect_rejection("silently omitted card", lambda: validate_packet(omitted_card, catalog_digest, allow_test_only=True))

    incomplete_totals = copy.deepcopy(base)
    incomplete_totals["interventions"]["totals"]["minutes"] = 0
    expect_rejection("incomplete intervention totals", lambda: validate_packet(incomplete_totals, catalog_digest, allow_test_only=True))

    candidate_as_baseline = copy.deepcopy(base)
    candidate_as_baseline["baseline"]["candidate_identity"] = "forbidden-candidate"
    expect_rejection("candidate result presented as baseline", lambda: validate_packet(candidate_as_baseline, catalog_digest, allow_test_only=True))

    expect_rejection("path move", lambda: reject_path_moves("R100\tdocs/README.md\tdocs/index.md", {"docs/README.md"}))
    expect_rejection("ordinary-task Harness call", lambda: reject_core_calls([{"command": "scripts/bin/harness audit"}]))


def validate_story_packet() -> None:
    story = ROOT / "docs" / "stories" / "US-110-v1-dogfood-pilot-baselines"
    for name in ["overview.md", "design.md", "execplan.md", "validation.md"]:
        check((story / name).is_file() and (story / name).stat().st_size > 0, f"US-110 packet file missing: {name}")
    overview = (story / "overview.md").read_text(encoding="utf-8")
    validation = (story / "validation.md").read_text(encoding="utf-8")
    check("pilot authorization" in overview.lower(), "US-110 does not preserve pilot authorization boundary")
    check("Phase 5 is not accepted" in validation, "US-110 must not claim Phase 5 acceptance")


def load_live_packet(directory: Path) -> dict[str, dict[str, Any]]:
    names = {
        "enrollment": "enrollment.json", "environment": "environment.json", "eligibility": "eligibility.json",
        "signature": "card-set.signature.json", "interventions": "interventions.json", "baseline": "baseline-result.json",
    }
    return {key: load_json(directory / filename) for key, filename in names.items()}


def require_live_evidence(catalog_digest: str) -> None:
    index = load_json(EVAL / "evidence" / "index.json")
    validate(index, schema("evidence-index"), "evidence index")
    check(index["status"] == "complete", "Phase 5 evidence index is not complete")
    check(len(index["pilots"]) >= 2, "Phase 5 requires at least two authorized pilots")
    packets = []
    for relative in index["pilots"]:
        directory = EVAL / "evidence" / relative
        check(directory.is_dir(), f"pilot evidence directory is absent: {relative}")
        packet = load_live_packet(directory)
        validate_packet(packet, catalog_digest)
        packets.append(packet)
    ids = [packet["enrollment"]["pilot_id"] for packet in packets]
    check(len(ids) == len(set(ids)), "pilot evidence repeats one pilot identity")
    for packet in packets:
        unrelated = set(packet["enrollment"]["unrelated_to"])
        check(any(other != packet["enrollment"]["pilot_id"] and other in unrelated for other in ids), "pilots are not recorded as unrelated")
    check(not index["blockers"], "complete evidence index still contains blockers")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-pilot-baselines", action="store_true")
    parser.add_argument("--dogfood-only", action="store_true")
    arguments = parser.parse_args()

    proof("Repository Harness useful paths are mapped in place at immutable Phase 4 source bytes", validate_dogfood)
    if arguments.dogfood_only:
        print("V1 Phase 5 Repository Harness dogfood verification passed (1 proof group)")
        return

    catalog_digest = validate_catalog()
    proof("Draft 2020-12 schemas, fixed P0-P7 catalog, and honest empty evidence index validate", lambda: validate_evidence_index(catalog_digest))
    packet = synthetic_packet(catalog_digest)
    proof("test-only positive packet satisfies enrollment, lock, signature, totals, and baseline contracts", lambda: validate_packet(packet, catalog_digest, allow_test_only=True))
    proof("negative contracts fail closed for every required Phase 5 evidence defect", lambda: validate_negative_contracts(catalog_digest))
    proof("US-110 remains a high-risk candidate packet without pilot or Phase 5 acceptance claims", validate_story_packet)

    if arguments.require_pilot_baselines:
        try:
            require_live_evidence(catalog_digest)
        except VerificationError as error:
            index = load_json(EVAL / "evidence" / "index.json")
            print(f"V1 Phase 5 live pilot evidence blocked: {error}", file=sys.stderr)
            for blocker in index.get("blockers", []):
                print(f"- {blocker}", file=sys.stderr)
            raise SystemExit(2) from error
        proof("two unrelated authorized pilots have complete signed baseline packets", lambda: None)

    print(f"V1 Phase 5 candidate verification passed ({PASS_COUNT} executable proof groups)")


if __name__ == "__main__":
    try:
        main()
    except VerificationError as error:
        print(f"V1 Phase 5 candidate verification failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

#!/usr/bin/env python3
"""Fail-closed Phase 5 dogfood and authenticated pilot-baseline verifier."""

from __future__ import annotations

import argparse
from collections import defaultdict
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "tests" / "evals" / "v1-phase5"
EVIDENCE = EVAL / "evidence"
SCHEMAS = EVAL / "schemas"
CARDS = {f"P{number}" for number in range(8)}
RFC3339_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
NAMESPACE = "repository-harness-phase5"
CORE_PACKET_FILES = {
    "enrollment.json", "environment.json", "eligibility.json",
    "interventions.json", "baseline-result.json", "repository.bundle",
}
ORDINARY_ARGV = [
    ["rg", "--no-config", "-q", "Phases 1-4 accepted / Phase 5 candidate", "docs/stories/US-105-harness-v1-implementation/overview.md"],
    ["rg", "--no-config", "-q", "Phase 6 remains not started", "docs/stories/US-105-harness-v1-implementation/validation.md"],
    ["git", "--no-optional-locks", "diff", "--no-ext-diff", "--check"],
]


class VerificationError(RuntimeError):
    pass


PASS_COUNT = 0
NEGATIVE_COUNT = 0


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
        try:
            shown = path.relative_to(ROOT)
        except ValueError:
            shown = path
        raise VerificationError(f"cannot read JSON {shown}: {error}") from error


def write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as error:
        raise VerificationError(f"cannot hash evidence file {path}: {error}") from error


def canonical_bytes(document: dict[str, Any], omitted: str | None = None) -> bytes:
    payload = {key: value for key, value in document.items() if key != omitted}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def canonical_digest(document: dict[str, Any], omitted: str) -> str:
    return sha256_bytes(canonical_bytes(document, omitted))


def hardened_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ)
    for name in list(environment):
        if name.startswith("GIT_CONFIG_") or name.startswith("GIT_ALIAS_"):
            environment.pop(name, None)
    for name in ["GIT_DIR", "GIT_WORK_TREE", "GIT_EXEC_PATH", "GIT_EXTERNAL_DIFF", "RIPGREP_CONFIG_PATH"]:
        environment.pop(name, None)
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1", "GIT_PAGER": "cat", "PAGER": "cat",
    })
    if extra:
        environment.update(extra)
    return environment


def run(
    arguments: list[str], *, cwd: Path = ROOT, input_bytes: bytes | None = None,
    expected: int = 0, environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            arguments, cwd=cwd, input=input_bytes, stdin=None if input_bytes is not None else subprocess.DEVNULL,
            capture_output=True, check=False, env=environment or hardened_env(),
        )
    except OSError as error:
        raise VerificationError(f"cannot execute {arguments[0]}: {error.strerror or error}") from error
    if completed.returncode != expected:
        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise VerificationError(
            f"command returned {completed.returncode}, expected {expected}: {arguments!r}\nstdout:\n{stdout}\nstderr:\n{stderr}"
        )
    return completed


def output(arguments: list[str], *, cwd: Path = ROOT) -> str:
    return run(arguments, cwd=cwd).stdout.decode("utf-8", errors="strict").strip()


def schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMAS / f"{name}.schema.json")


def validate(instance: Any, contract: dict[str, Any], location: str = "$") -> None:
    expected_type = contract.get("type")
    matches = {
        "object": isinstance(instance, dict), "array": isinstance(instance, list),
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
        missing = sorted(set(contract.get("required", [])) - set(instance))
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
        if "items" in contract:
            for index, value in enumerate(instance):
                validate(value, contract["items"], f"{location}[{index}]")
    elif isinstance(instance, str):
        check(len(instance) >= contract.get("minLength", 0), f"{location}: string is too short")
        if "pattern" in contract:
            check(re.fullmatch(contract["pattern"], instance) is not None, f"{location}: string does not match pattern")
    elif isinstance(instance, int) and not isinstance(instance, bool) and "minimum" in contract:
        check(instance >= contract["minimum"], f"{location}: integer is below minimum")


def parse_time(value: str, field: str) -> datetime:
    check(RFC3339_UTC.fullmatch(value) is not None, f"{field}: timestamp must be strict RFC 3339 UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise VerificationError(f"{field}: invalid RFC 3339 UTC timestamp") from error
    check(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value, f"{field}: timestamp is not canonical")
    return parsed


def canonical_repository(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise VerificationError(f"repository identity is malformed: {value}") from error
    check(parsed.scheme == "https" and parsed.hostname is not None, "repository identity must use canonical https")
    try:
        port = parsed.port
    except ValueError as error:
        raise VerificationError("repository identity contains an invalid port") from error
    check(parsed.username is None and parsed.password is None and port is None, "repository identity contains authority aliases")
    check(not parsed.query and not parsed.fragment and not parsed.path.endswith("/"), "repository identity contains query, fragment, or trailing slash")
    check("%" not in value and "\\" not in value and "//" not in parsed.path, "repository identity contains encoded or ambiguous path syntax")
    parts = PurePosixPath(parsed.path).parts
    check(parts and parts[-1].endswith(".git") and all(part not in {".", ".."} for part in parts), "repository identity must end in an unambiguous .git path")
    normalized = f"https://{parsed.hostname.lower()}{parsed.path}"
    check(value == normalized, "repository identity is not canonical")
    return normalized


def relative_name(value: str, field: str) -> PurePosixPath:
    check(value and "\\" not in value, f"{field}: path is empty or contains backslashes")
    candidate = PurePosixPath(value)
    check(not candidate.is_absolute(), f"{field}: absolute path is prohibited")
    check(all(part not in {"", ".", ".."} for part in candidate.parts), f"{field}: traversal is prohibited")
    check(str(candidate) == value, f"{field}: path is not canonical POSIX form")
    return candidate


def contained_member(root: Path, value: str, field: str, *, directory: bool = False) -> Path:
    relative = relative_name(value, field)
    current = root
    check(root.exists() and not root.is_symlink(), f"{field}: custody root is absent or a symlink")
    for part in relative.parts:
        current = current / part
        try:
            mode = current.lstat()
        except OSError as error:
            raise VerificationError(f"{field}: custody member is absent: {value}") from error
        check(not current.is_symlink(), f"{field}: symlink custody member is prohibited: {value}")
    check(current.is_dir() if directory else current.is_file(), f"{field}: wrong custody member type: {value}")
    try:
        current.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise VerificationError(f"{field}: custody member escaped root: {value}") from error
    return current


def exact_cards(records: list[dict[str, Any]], location: str) -> None:
    identifiers = [record.get("card_id") for record in records]
    check(set(identifiers) == CARDS and len(identifiers) == 8, f"{location}: expected exactly P0-P7, found {identifiers}")


def validate_catalog() -> tuple[str, dict[str, dict[str, Any]]]:
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        contract = load_json(path)
        check(contract.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"schema draft changed: {path.name}")
        check(contract.get("type") == "object", f"top-level schema is not an object: {path.name}")
    catalog_path = EVAL / "cards" / "catalog.json"
    catalog = load_json(catalog_path)
    check(catalog.get("schema") == "repository-harness-pilot-card-catalog/v1" and catalog.get("catalog_revision") == 1, "card catalog identity changed")
    exact_cards(catalog.get("cards", []), "card catalog")
    cards: dict[str, dict[str, Any]] = {}
    for entry in catalog["cards"]:
        path = EVAL / entry["path"]
        check(path.parent == EVAL / "cards" and path.is_file() and not path.is_symlink(), f"card path escaped or is missing: {entry['path']}")
        check(sha256_file(path) == entry["sha256"], f"card digest changed: {entry['card_id']}")
        card = load_json(path)
        validate(card, schema("card"), f"card {entry['card_id']}")
        check(card["card_id"] == entry["card_id"], f"card identity/path mismatch: {entry['card_id']}")
        cards[entry["card_id"]] = card
    return sha256_file(catalog_path), cards


def reject_path_moves(name_status: str, mapped_paths: set[str]) -> None:
    for line in name_status.splitlines():
        fields = line.split("\t")
        if fields[0].startswith("R"):
            raise VerificationError(f"path move is prohibited: {fields[1]} -> {fields[2]}")
        if fields[0] == "D" and len(fields) > 1 and fields[1] in mapped_paths:
            raise VerificationError(f"mapped useful path was deleted: {fields[1]}")


def execute_ordinary_task(commands: list[dict[str, Any]]) -> None:
    actual = [entry.get("argv") for entry in commands]
    check(actual == ORDINARY_ARGV, f"ordinary task argv differs from the closed grammar: {actual}")
    for entry in commands:
        completed = run(entry["argv"], expected=entry["exit_code"])
        check(completed.returncode == 0, f"ordinary task check failed: {entry['argv']}")


def validate_dogfood() -> None:
    mapping = load_json(EVAL / "dogfood" / "repository-map.json")
    validate(mapping, schema("dogfood-map"), "dogfood map")
    dispositions = {entry["path"]: entry["disposition"] for entry in load_json(ROOT / "release" / "contracts" / "v1" / "path-dispositions.json")["entries"]}
    source = mapping["source_revision"]
    check(output(["git", "cat-file", "-t", source]) == "commit", "dogfood source revision is missing")
    paths = [role["path"] for role in mapping["roles"]]
    check(len(paths) == len(set(paths)), "dogfood map duplicates a useful path")
    for role in mapping["roles"]:
        path = role["path"]
        check(dispositions.get(path) == "target-owned-destination", f"dogfood role violates Phase 1 disposition: {path}")
        check((ROOT / path).is_file(), f"mapped useful path is absent: {path}")
        check(output(["git", "rev-parse", f"{source}:{path}"]) == role["source_blob"], f"source blob changed for {path}")
        payload = run(["git", "show", f"{source}:{path}"]).stdout
        check(sha256_bytes(payload) == role["source_sha256"], f"source bytes changed for {path}")
    reject_path_moves(output(["git", "diff", "--name-status", source, "--"]), set(paths))
    task = load_json(EVAL / "dogfood" / "ordinary-task.json")
    validate(task, schema("ordinary-task"), "ordinary task")
    check(task["starting_revision"] == source and task["core_command_count"] == 0, "ordinary task identity/count changed")
    execute_ordinary_task(task["commands"])


def intervention_totals(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_card: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"event_count": 0, "minutes": 0})
    by_taxonomy: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"event_count": 0, "minutes": 0})
    for event in events:
        for bucket, key in [(by_card, event["card_id"]), (by_taxonomy, event["taxonomy"])]:
            bucket[key]["event_count"] += 1
            bucket[key]["minutes"] += event["minutes"]
    return {"event_count": len(events), "minutes": sum(event["minutes"] for event in events), "by_card": dict(sorted(by_card.items())), "by_taxonomy": dict(sorted(by_taxonomy.items()))}


def validate_environment(document: dict[str, Any], artifact_digests: dict[str, str]) -> None:
    validate(document, schema("environment-lock"), "environment lock")
    check(document["environment_sha256"] == canonical_digest(document, "environment_sha256"), "environment digest mismatch")
    tools = [tool["name"] for tool in document["tools"]]
    check(len(tools) == len(set(tools)), "environment tools are not uniquely versioned")
    enabled = document["enabled_tools"]
    check(len(enabled) == len(set(enabled)) and set(enabled) <= set(tools), "enabled tools are duplicated or absent from versioned tools")
    exact_cards(document["acceptance_commands"], "environment acceptance commands")
    for fixture in document["fixtures"]:
        check(artifact_digests.get(fixture["path"]) == fixture["sha256"], f"fixture is outside authenticated custody or has wrong digest: {fixture['path']}")


def validate_eligibility(document: dict[str, Any], artifact_digests: dict[str, str]) -> None:
    validate(document, schema("eligibility"), "eligibility")
    exact_cards(document["cards"], "eligibility")
    for card in document["cards"]:
        if card["disposition"] == "inapplicable":
            check(card["finding"].strip() and card["finding_artifacts"], f"{card['card_id']} lacks authenticated inapplicability evidence")
        else:
            check(not card["finding"] and not card["finding_artifacts"], f"{card['card_id']} eligible record contains contradictory inapplicability data")
        for path in card["finding_artifacts"]:
            check(path in artifact_digests, f"inapplicability evidence is outside authenticated manifest: {path}")


def validate_interventions(document: dict[str, Any]) -> None:
    validate(document, schema("intervention-log"), "intervention log")
    check(document["totals"] == intervention_totals(document["events"]), "intervention totals are incomplete or changed")


def validate_baseline(document: dict[str, Any], artifact_digests: dict[str, str]) -> None:
    validate(document, schema("baseline-result"), "baseline result")
    exact_cards(document["cards"], "baseline result")
    subject = document["evaluation_subject"]
    check(
        artifact_digests.get(subject["artifact"]) == subject["sha256"],
        "pre-candidate baseline subject is outside authenticated custody or has wrong digest",
    )
    check(document["result_sha256"] == canonical_digest(document, "result_sha256"), "baseline result digest mismatch")


def load_trusted_owners(evidence_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    path = contained_member(evidence_root, "trusted-owners.json", "trusted owners")
    document = load_json(path)
    validate(document, schema("trusted-owners"), "trusted owners")
    owners: dict[str, dict[str, Any]] = {}
    for owner in document["owners"]:
        check(owner["owner_id"] not in owners, f"trusted owner identity is duplicated: {owner['owner_id']}")
        canonical_repository(owner["canonical_repository"])
        check(owner["public_key"].split()[0] == "ssh-ed25519", "trusted owner key is not Ed25519")
        parse_time(owner["trusted_at"], "trusted owner time")
        owners[owner["owner_id"]] = owner
    return document, owners


def validate_manifest(packet_dir: Path, pilot_id: str) -> tuple[dict[str, Any], dict[str, str]]:
    manifest_path = contained_member(packet_dir, "packet-manifest.json", "packet manifest")
    manifest = load_json(manifest_path)
    validate(manifest, schema("packet-manifest"), "packet manifest")
    check(manifest["pilot_id"] == pilot_id == packet_dir.name, "pilot directory, manifest, and index identity differ")
    entries = manifest["artifacts"]
    paths = [entry["path"] for entry in entries]
    check(len(paths) == len(set(paths)), "packet manifest contains duplicate artifact paths")
    check(CORE_PACKET_FILES <= set(paths), f"packet manifest omits core artifacts: {sorted(CORE_PACKET_FILES - set(paths))}")
    digests: dict[str, str] = {}
    for entry in entries:
        path = contained_member(packet_dir, entry["path"], "packet artifact")
        digest = sha256_file(path)
        check(digest == entry["sha256"], f"packet artifact digest mismatch: {entry['path']}")
        digests[entry["path"]] = digest
    actual_files: set[str] = set()
    for path in packet_dir.rglob("*"):
        check(not path.is_symlink(), f"packet contains symlink: {path.relative_to(packet_dir)}")
        if path.is_file():
            actual_files.add(path.relative_to(packet_dir).as_posix())
    expected_files = set(paths) | {"packet-manifest.json", "authentication.json"}
    check(actual_files == expected_files, f"packet manifest is not complete: missing={sorted(expected_files - actual_files)} unlisted={sorted(actual_files - expected_files)}")
    return manifest, digests


def verify_owner_authentication(authentication: dict[str, Any], trusted: dict[str, dict[str, Any]]) -> dict[str, Any]:
    validate(authentication, schema("signature"), "packet authentication")
    owner_id = authentication["owner_id"]
    check(owner_id in trusted, "packet owner is not independently trusted")
    owner = trusted[owner_id]
    statement = authentication["statement"]
    check(statement["owner_id"] == owner_id, "authentication owner identity mismatch")
    check(authentication["algorithm"] == "ssh-ed25519" and authentication["namespace"] == NAMESPACE, "unknown authentication algorithm or namespace")
    with tempfile.TemporaryDirectory(prefix="phase5-auth-") as temporary:
        temp = Path(temporary)
        allowed = temp / "allowed_signers"
        signature = temp / "statement.sig"
        allowed.write_text(f"{owner_id} namespaces=\"{NAMESPACE}\" {owner['public_key']}\n", encoding="utf-8")
        signature.write_text(authentication["signature"], encoding="utf-8")
        run(["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", owner_id, "-n", NAMESPACE, "-s", str(signature)], input_bytes=canonical_bytes(statement))
    return owner


def resolve_bundle_commit(bundle: Path, revision: str) -> None:
    check(COMMIT.fullmatch(revision) is not None, "starting revision is not a full Git commit")
    with tempfile.TemporaryDirectory(prefix="phase5-bundle-") as temporary:
        repository = Path(temporary) / "repository.git"
        run(["git", "init", "--bare", str(repository)])
        run(["git", "bundle", "verify", str(bundle)], cwd=repository)
        run(["git", "bundle", "unbundle", str(bundle)], cwd=repository)
        run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=repository)


def validate_timeline(
    enrollment: dict[str, Any], environment: dict[str, Any], eligibility: dict[str, Any],
    interventions: dict[str, Any], baseline: dict[str, Any], statement: dict[str, Any], owner: dict[str, Any],
) -> None:
    trusted_at = parse_time(owner["trusted_at"], "trusted_at")
    authorized = parse_time(enrollment["authorized_at"], "authorized_at")
    locked = parse_time(environment["locked_at"], "locked_at")
    evaluated = parse_time(eligibility["evaluated_at"], "evaluated_at")
    started = parse_time(baseline["started_at"], "baseline.started_at")
    completed = parse_time(baseline["completed_at"], "baseline.completed_at")
    published = parse_time(statement["published_at"], "published_at")
    disclosure = parse_time(statement["candidate_disclosure_not_before"], "candidate_disclosure_not_before")
    check(trusted_at <= authorized <= locked <= started, "trust/authorization/environment/baseline start order is invalid")
    check(authorized <= evaluated <= started, "eligibility was not fixed before baseline start")
    check(started <= completed <= published <= disclosure, "baseline completed or published after candidate disclosure cutoff")
    check(statement["baseline_started_at"] == baseline["started_at"] and statement["baseline_completed_at"] == baseline["completed_at"], "authenticated publication does not bind baseline times")
    for event in interventions["events"]:
        timestamp = parse_time(event["timestamp"], f"intervention {event['card_id']} timestamp")
        check(started <= timestamp <= completed, "intervention falls outside baseline run")


def validate_packet(
    packet_dir: Path, pilot_id: str, trusted: dict[str, dict[str, Any]],
    catalog_digest: str, cards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    check(packet_dir.name == pilot_id, "pilot directory name does not match evidence index")
    manifest, artifact_digests = validate_manifest(packet_dir, pilot_id)
    authentication = load_json(contained_member(packet_dir, "authentication.json", "packet authentication"))
    enrollment = load_json(contained_member(packet_dir, "enrollment.json", "enrollment"))
    environment = load_json(contained_member(packet_dir, "environment.json", "environment"))
    eligibility = load_json(contained_member(packet_dir, "eligibility.json", "eligibility"))
    interventions = load_json(contained_member(packet_dir, "interventions.json", "interventions"))
    baseline = load_json(contained_member(packet_dir, "baseline-result.json", "baseline result"))
    validate(enrollment, schema("pilot-enrollment"), "pilot enrollment")
    validate_environment(environment, artifact_digests)
    validate_eligibility(eligibility, artifact_digests)
    validate_interventions(interventions)
    validate_baseline(baseline, artifact_digests)
    owner = verify_owner_authentication(authentication, trusted)
    statement = authentication["statement"]
    repository = canonical_repository(enrollment["canonical_repository"])
    check(repository == canonical_repository(owner["canonical_repository"]) == statement["canonical_repository"], "repository identity is not independently bound")
    check(enrollment["owner_id"] == owner["owner_id"] == statement["owner_id"], "owner identity mismatch")
    check(enrollment["authorization_scope"] == owner["authorization_scope"] == statement["authorization_scope"], "authorization scope mismatch")
    check(enrollment["card_set_sha256"] == baseline["card_set_sha256"] == statement["card_catalog_sha256"] == catalog_digest, "card catalog binding mismatch")
    revision = enrollment["starting_revision"]["value"]
    check(revision == baseline["starting_revision"] == statement["starting_revision"], "immutable starting revision changed")
    check(statement["packet_manifest_sha256"] == sha256_file(packet_dir / "packet-manifest.json"), "authenticated packet-manifest digest mismatch")
    check(statement["pilot_id"] == pilot_id and manifest["pilot_id"] == pilot_id, "pilot identity mismatch")
    check(statement["custody_id"] == manifest["custody_id"], "authenticated custody identity mismatch")
    check(statement["publication_id"].startswith(f"{pilot_id}-baseline-"), "baseline publication identity is not pilot-bound")
    subject = baseline["evaluation_subject"]
    check(
        statement["baseline_subject_identity"] == subject["identity"]
        and statement["baseline_subject_sha256"] == subject["sha256"],
        "authenticated publication does not bind the pre-candidate baseline subject",
    )
    bundle_path = enrollment["starting_revision"]["repository_bundle"]
    check(bundle_path in artifact_digests, "repository bundle is outside authenticated packet manifest")
    resolve_bundle_commit(contained_member(packet_dir, bundle_path, "repository bundle"), revision)
    for name, document in [("environment", environment), ("eligibility", eligibility), ("interventions", interventions), ("baseline", baseline)]:
        check(document["pilot_id"] == pilot_id, f"{name} belongs to another pilot")
    check(environment["evaluator_id"] == eligibility["evaluator_id"], "eligibility evaluator differs from environment lock")
    check(baseline["environment_sha256"] == environment["environment_sha256"], "baseline environment changed after lock")
    check(baseline["intervention_log"] == "interventions.json", "baseline does not directly name the intervention log")
    check(baseline["intervention_log_sha256"] == artifact_digests["interventions.json"], "baseline intervention binding mismatch")
    commands = {entry["card_id"]: canonical_bytes({"argv": entry["argv"]}).decode("utf-8") for entry in environment["acceptance_commands"]}
    dispositions = {entry["card_id"]: entry for entry in eligibility["cards"]}
    for result in baseline["cards"]:
        card_id = result["card_id"]
        disposition = dispositions[card_id]
        if disposition["disposition"] == "inapplicable":
            check(result["outcome"] == "inapplicable" and result["acceptance_command"] == "inapplicable", f"{card_id} inapplicability/result mismatch")
            authenticated_findings = set(disposition["finding_artifacts"])
            check(all(item["artifact"] in authenticated_findings for item in result["evidence"]), f"{card_id} inapplicability result lacks authenticated finding evidence")
        else:
            check(result["outcome"] != "inapplicable" and result["acceptance_command"] == commands[card_id], f"{card_id} result lacks its locked acceptance command")
            requirements = [item["requirement"] for item in result["evidence"]]
            check(requirements == cards[card_id]["evidence_requirements"], f"{card_id} does not back every card-specific evidence requirement")
        for item in result["evidence"]:
            check(item["artifact"] in artifact_digests, f"{card_id} evidence is outside authenticated custody: {item['artifact']}")
    validate_timeline(enrollment, environment, eligibility, interventions, baseline, statement, owner)
    return {"pilot_id": pilot_id, "repository": repository, "owner_id": owner["owner_id"], "owner_identity": owner["owner_identity"]}


def validate_pilot_independence(packets: list[dict[str, Any]]) -> None:
    repositories = [packet["repository"] for packet in packets]
    owner_ids = [packet["owner_id"] for packet in packets]
    identities = [packet["owner_identity"] for packet in packets]
    check(len(repositories) == len(set(repositories)), "pilots reuse the same canonical repository")
    check(len(owner_ids) == len(set(owner_ids)) and len(identities) == len(set(identities)), "pilots reuse the same owner identity")


def load_evidence_index(evidence_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    index = load_json(contained_member(evidence_root, "index.json", "evidence index"))
    validate(index, schema("evidence-index"), "evidence index")
    check(len(index["pilots"]) == len(set(index["pilots"])), "evidence index duplicates a pilot")
    _, owners = load_trusted_owners(evidence_root)
    if index["status"] == "candidate-awaiting-pilot-authorization":
        check(not index["pilots"] and index["blockers"], "candidate evidence index hides pilots or blockers")
    else:
        check(len(index["pilots"]) >= 2 and not index["blockers"], "complete evidence index is shallow or contradictory")
    return index, owners


def require_live_evidence(evidence_root: Path, catalog_digest: str, cards: dict[str, dict[str, Any]]) -> None:
    index, owners = load_evidence_index(evidence_root)
    check(index["status"] == "complete", "Phase 5 evidence index is not complete")
    packets = []
    for pilot_id in index["pilots"]:
        relative_name(pilot_id, "pilot directory")
        packet_dir = contained_member(evidence_root, pilot_id, "pilot directory", directory=True)
        packets.append(validate_packet(packet_dir, pilot_id, owners, catalog_digest, cards))
    validate_pilot_independence(packets)


def verify_index_mode(
    index: dict[str, Any], evidence_root: Path, catalog_digest: str,
    cards: dict[str, dict[str, Any]], *, require_live: bool,
) -> bool:
    if index["status"] == "complete" or require_live:
        require_live_evidence(evidence_root, catalog_digest, cards)
        return True
    return False


def make_git_bundle(root: Path) -> tuple[Path, str]:
    root.mkdir(parents=True)
    repository = root / "source"
    repository.mkdir()
    run(["git", "init", str(repository)])
    (repository / "README.md").write_text("synthetic authenticated pilot fixture\n", encoding="utf-8")
    run(["git", "add", "README.md"], cwd=repository)
    environment = hardened_env({
        "GIT_AUTHOR_NAME": "Synthetic Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
    })
    run(["git", "commit", "-m", "synthetic fixture"], cwd=repository, environment=environment)
    revision = output(["git", "rev-parse", "HEAD"], cwd=repository)
    bundle = root / "repository.bundle"
    run(["git", "bundle", "create", str(bundle), "HEAD"], cwd=repository)
    return bundle, revision


def sign_statement(private_key: Path, statement: dict[str, Any]) -> str:
    with tempfile.TemporaryDirectory(prefix="phase5-sign-") as temporary:
        statement_path = Path(temporary) / "statement.json"
        statement_path.write_bytes(canonical_bytes(statement))
        run(["ssh-keygen", "-Y", "sign", "-f", str(private_key), "-n", NAMESPACE, str(statement_path)])
        return (Path(str(statement_path) + ".sig")).read_text(encoding="utf-8")


def build_synthetic_packet(root: Path) -> tuple[Path, dict[str, dict[str, Any]], Path, dict[str, dict[str, Any]], str]:
    catalog_digest, cards = validate_catalog()
    pilot_id = "synthetic-pilot-a"
    packet = root / pilot_id
    packet.mkdir(parents=True)
    key = root / "owner-key"
    run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)])
    public_key = " ".join((Path(str(key) + ".pub")).read_text(encoding="utf-8").split()[:2])
    bundle, revision = make_git_bundle(root / "git-evidence")
    shutil.copyfile(bundle, packet / "repository.bundle")
    fixture_path = packet / "artifacts" / "fixture.txt"
    fixture_path.parent.mkdir()
    fixture_path.write_text("locked fixture\n", encoding="utf-8")
    baseline_subject_path = packet / "artifacts" / "baseline-subject.txt"
    baseline_subject_path.write_text("synthetic pre-candidate baseline subject\n", encoding="utf-8")
    authorized = "2000-01-01T00:00:10Z"
    started = "2000-01-01T01:00:00Z"
    completed = "2000-01-01T02:00:00Z"
    enrollment = {
        "schema": "repository-harness-pilot-enrollment/v2", "pilot_id": pilot_id,
        "canonical_repository": "https://example.test/synthetic-a.git", "owner_id": "synthetic-owner-a",
        "authorization_scope": "synthetic offline verifier fixture", "authorized_at": authorized,
        "starting_revision": {"kind": "git-commit", "value": revision, "repository_bundle": "repository.bundle"},
        "card_set_sha256": catalog_digest,
    }
    commands = [{"card_id": f"P{number}", "argv": ["synthetic-check", f"P{number}"]} for number in range(8)]
    environment = {
        "schema": "repository-harness-environment-lock/v2", "pilot_id": pilot_id, "locked_at": "2000-01-01T00:00:20Z",
        "model": "synthetic-model", "reasoning": "synthetic", "operating_system": "synthetic-os", "architecture": "synthetic-arch",
        "tools": [{"name": "synthetic-check", "version": "1"}], "enabled_tools": ["synthetic-check"], "permissions": ["synthetic-read-write"],
        "evaluator_id": "synthetic-evaluator", "fixtures": [{"path": "artifacts/fixture.txt", "sha256": sha256_file(fixture_path)}],
        "acceptance_commands": commands, "environment_sha256": "",
    }
    environment["environment_sha256"] = canonical_digest(environment, "environment_sha256")
    eligibility = {
        "schema": "repository-harness-pilot-eligibility/v2", "pilot_id": pilot_id,
        "evaluated_at": "2000-01-01T00:00:30Z", "evaluator_id": "synthetic-evaluator",
        "cards": [{"card_id": f"P{number}", "disposition": "eligible", "finding": "", "finding_artifacts": []} for number in range(8)],
    }
    interventions = {
        "schema": "repository-harness-intervention-log/v2", "pilot_id": pilot_id, "run_kind": "baseline",
        "events": [{"card_id": "P0", "actor": "synthetic-evaluator", "timestamp": "2000-01-01T01:30:00Z", "taxonomy": "environment/setup", "reason": "exercise authenticated totals", "minutes": 2, "changed_outcome": False}],
        "totals": {},
    }
    interventions["totals"] = intervention_totals(interventions["events"])
    results = []
    for number in range(8):
        card_id = f"P{number}"
        evidence = []
        for index, requirement in enumerate(cards[card_id]["evidence_requirements"]):
            relative = f"artifacts/{card_id}-evidence-{index}.txt"
            path = packet / relative
            path.write_text(f"synthetic evidence for {card_id}: {requirement}\n", encoding="utf-8")
            evidence.append({"requirement": requirement, "artifact": relative})
        command = canonical_bytes({"argv": commands[number]["argv"]}).decode("utf-8")
        results.append({"card_id": card_id, "outcome": "passed", "acceptance_command": command, "evidence": evidence})
    for name, document in [("enrollment.json", enrollment), ("environment.json", environment), ("eligibility.json", eligibility), ("interventions.json", interventions)]:
        write_json(packet / name, document)
    baseline = {
        "schema": "repository-harness-baseline-result/v2", "pilot_id": pilot_id, "run_kind": "baseline",
        "evaluation_subject": {
            "kind": "pre-candidate-baseline", "identity": "synthetic-v0-baseline",
            "artifact": "artifacts/baseline-subject.txt", "sha256": sha256_file(baseline_subject_path),
        },
        "started_at": started, "completed_at": completed, "starting_revision": revision,
        "card_set_sha256": catalog_digest, "environment_sha256": environment["environment_sha256"], "cards": results,
        "intervention_log": "interventions.json", "intervention_log_sha256": sha256_file(packet / "interventions.json"), "result_sha256": "",
    }
    baseline["result_sha256"] = canonical_digest(baseline, "result_sha256")
    write_json(packet / "baseline-result.json", baseline)
    artifacts = []
    for path in sorted(candidate for candidate in packet.rglob("*") if candidate.is_file()):
        relative = path.relative_to(packet).as_posix()
        artifacts.append({"path": relative, "sha256": sha256_file(path), "media_type": "application/octet-stream", "purpose": "synthetic authenticated verifier fixture"})
    manifest = {"schema": "repository-harness-pilot-packet-manifest/v2", "pilot_id": pilot_id, "custody_id": "synthetic-pilot-a-custody-1", "artifacts": artifacts}
    write_json(packet / "packet-manifest.json", manifest)
    statement = {
        "schema": "repository-harness-authenticated-baseline-publication/v2", "pilot_id": pilot_id,
        "canonical_repository": enrollment["canonical_repository"], "starting_revision": revision,
        "owner_id": enrollment["owner_id"], "authorization_scope": enrollment["authorization_scope"],
        "card_catalog_sha256": catalog_digest, "packet_manifest_sha256": sha256_file(packet / "packet-manifest.json"),
        "publication_id": "synthetic-pilot-a-baseline-publication-1", "custody_id": manifest["custody_id"],
        "baseline_subject_identity": baseline["evaluation_subject"]["identity"],
        "baseline_subject_sha256": baseline["evaluation_subject"]["sha256"],
        "baseline_started_at": started, "baseline_completed_at": completed, "published_at": "2000-01-01T02:10:00Z",
        "candidate_disclosure_not_before": "2000-01-01T03:00:00Z",
    }
    authentication = {"schema": "repository-harness-packet-authentication/v2", "owner_id": enrollment["owner_id"], "algorithm": "ssh-ed25519", "namespace": NAMESPACE, "statement": statement, "signature": sign_statement(key, statement)}
    write_json(packet / "authentication.json", authentication)
    trusted = {
        enrollment["owner_id"]: {
            "owner_id": enrollment["owner_id"], "owner_identity": "synthetic-independent-owner-a",
            "canonical_repository": enrollment["canonical_repository"], "authorization_scope": enrollment["authorization_scope"],
            "public_key": public_key, "trust_source": "synthetic independent verifier fixture", "trusted_at": "2000-01-01T00:00:00Z",
        }
    }
    return packet, trusted, key, cards, catalog_digest


def expect_rejection(label: str, function: Callable[[], None]) -> None:
    global NEGATIVE_COUNT
    try:
        function()
    except VerificationError:
        NEGATIVE_COUNT += 1
        return
    raise VerificationError(f"negative fixture was accepted: {label}")


def prove_positive_packet() -> None:
    with tempfile.TemporaryDirectory(prefix="phase5-positive-") as temporary:
        packet, trusted, _, cards, catalog_digest = build_synthetic_packet(Path(temporary))
        validate_packet(packet, packet.name, trusted, catalog_digest, cards)


def prove_negative_contracts() -> None:
    global NEGATIVE_COUNT
    NEGATIVE_COUNT = 0
    with tempfile.TemporaryDirectory(prefix="phase5-negative-") as temporary:
        root = Path(temporary)
        packet, trusted, key, cards, catalog_digest = build_synthetic_packet(root)
        authentication_path = packet / "authentication.json"
        original_auth = authentication_path.read_bytes()
        authentication = load_json(authentication_path)
        authentication["signature"] = "x"
        write_json(authentication_path, authentication)
        expect_rejection("one-character signature", lambda: validate_packet(packet, packet.name, trusted, catalog_digest, cards))
        authentication_path.write_bytes(original_auth)

        forged_live = load_json(authentication_path)
        forged_live["owner_id"] = "self-declared-owner"
        forged_live["algorithm"] = "ed25519"
        forged_live["statement"]["canonical_repository"] = "https://example.invalid/same.git"
        forged_live["statement"]["starting_revision"] = "1" * 40
        forged_live["statement"]["owner_id"] = "self-declared-owner"
        forged_live["statement"]["published_at"] = "not-a-time"
        forged_live["signature"] = "x"
        expect_rejection("confirmed self-declared forged live packet", lambda: verify_owner_authentication(forged_live, {}))

        unknown = load_json(authentication_path)
        unknown["algorithm"] = "ed25519"
        expect_rejection("unknown signature algorithm", lambda: verify_owner_authentication(unknown, trusted))
        malformed = copy.deepcopy(unknown["statement"])
        malformed["published_at"] = "not-a-time"
        expect_rejection("malformed signed time", lambda: parse_time(malformed["published_at"], "published_at"))
        late = copy.deepcopy(unknown["statement"])
        late["published_at"] = "2000-01-01T04:00:00Z"
        expect_rejection("post-candidate baseline publication", lambda: check(parse_time(late["published_at"], "published") <= parse_time(late["candidate_disclosure_not_before"], "disclosure"), "published after disclosure"))

        enrollment = load_json(packet / "enrollment.json")
        expect_rejection("arbitrary commit", lambda: resolve_bundle_commit(packet / "repository.bundle", "1" * 40))
        forged_owner = copy.deepcopy(trusted[enrollment["owner_id"]])
        forged_owner["canonical_repository"] = "https://example.invalid/same.git"
        expect_rejection("fake repository identity", lambda: check(canonical_repository(enrollment["canonical_repository"]) == canonical_repository(forged_owner["canonical_repository"]), "repository mismatch"))
        expect_rejection("changed enrolled revision", lambda: check(enrollment["starting_revision"]["value"] == "2" * 40, "revision mismatch"))

        intervention_path = packet / "interventions.json"
        original_interventions = intervention_path.read_bytes()
        changed = load_json(intervention_path)
        changed["events"][0]["minutes"] = 99
        write_json(intervention_path, changed)
        expect_rejection("unsigned intervention rewrite", lambda: validate_packet(packet, packet.name, trusted, catalog_digest, cards))
        intervention_path.write_bytes(original_interventions)

        eligibility = load_json(packet / "eligibility.json")
        eligibility["cards"].pop()
        expect_rejection("silently omitted card", lambda: validate_eligibility(eligibility, {}))
        incomplete_totals = load_json(packet / "interventions.json")
        incomplete_totals["totals"]["minutes"] = 0
        expect_rejection("incomplete intervention totals", lambda: validate_interventions(incomplete_totals))
        candidate_result = load_json(packet / "baseline-result.json")
        candidate_result["evaluation_subject"]["kind"] = "candidate"
        expect_rejection("candidate result presented as baseline", lambda: validate_baseline(candidate_result, {}))
        inapplicable = load_json(packet / "eligibility.json")
        inapplicable["cards"][0].update({"disposition": "inapplicable", "finding": "", "finding_artifacts": []})
        expect_rejection("unauthenticated inapplicability", lambda: validate_eligibility(inapplicable, {}))

        environment = load_json(packet / "environment.json")
        environment["enabled_tools"].append("missing-tool")
        expect_rejection("inconsistent environment", lambda: validate_environment(environment, {}))
        baseline_path = packet / "baseline-result.json"
        fake_evidence = load_json(baseline_path)
        fake_evidence["cards"][0]["evidence"][0]["artifact"] = "artifacts/not-real.txt"
        fake_evidence["result_sha256"] = canonical_digest(fake_evidence, "result_sha256")
        write_json(baseline_path, fake_evidence)
        manifest_path = packet / "packet-manifest.json"
        manifest = load_json(manifest_path)
        next(entry for entry in manifest["artifacts"] if entry["path"] == "baseline-result.json")["sha256"] = sha256_file(baseline_path)
        write_json(manifest_path, manifest)
        renewed = load_json(authentication_path)
        renewed["statement"]["packet_manifest_sha256"] = sha256_file(manifest_path)
        renewed["signature"] = sign_statement(key, renewed["statement"])
        write_json(authentication_path, renewed)
        expect_rejection("fake evidence artifact", lambda: validate_packet(packet, packet.name, trusted, catalog_digest, cards))

        expect_rejection("absolute evidence path", lambda: relative_name("/tmp/evidence", "artifact"))
        expect_rejection("parent traversal", lambda: relative_name("../evidence", "artifact"))
        symlink = packet / "artifacts" / "escape"
        try:
            symlink.symlink_to(packet / "enrollment.json")
            expect_rejection("symlink escape", lambda: contained_member(packet, "artifacts/escape", "artifact"))
        finally:
            symlink.unlink(missing_ok=True)
        expect_rejection("mismatched pilot directory", lambda: validate_packet(packet, "another-pilot", trusted, catalog_digest, cards))

        identity = {"pilot_id": "a", "repository": enrollment["canonical_repository"], "owner_id": "owner-a", "owner_identity": "person-a"}
        same_repository = {"pilot_id": "b", "repository": identity["repository"], "owner_id": "owner-b", "owner_identity": "person-b"}
        same_owner = {"pilot_id": "b", "repository": "https://example.test/synthetic-b.git", "owner_id": identity["owner_id"], "owner_identity": identity["owner_identity"]}
        expect_rejection("same repository dual pilots", lambda: validate_pilot_independence([identity, same_repository]))
        expect_rejection("same owner dual pilots", lambda: validate_pilot_independence([identity, same_owner]))

        shallow = root / "shallow-evidence"
        shallow.mkdir()
        write_json(shallow / "trusted-owners.json", {"schema": "repository-harness-trusted-pilot-owners/v1", "owners": []})
        write_json(shallow / "index.json", {"schema": "repository-harness-phase5-evidence-index/v2", "phase": 5, "status": "complete", "card_catalog": "cards/catalog.json", "trusted_owners": "trusted-owners.json", "pilots": ["pilot-a", "pilot-b"], "blockers": []})
        shallow_index = load_json(shallow / "index.json")
        expect_rejection("shallow complete index through default dispatch", lambda: verify_index_mode(shallow_index, shallow, catalog_digest, cards, require_live=False))

        alias = ["git", "-c", "alias.h=!scripts/bin/harness audit", "h"]
        expect_rejection("Git alias core-call bypass", lambda: check(alias in ORDINARY_ARGV, "argv outside closed grammar"))
        expect_rejection("subprocess OSError", lambda: run(["phase5-command-that-does-not-exist"]))

        wrapper_path = ROOT / "scripts" / "verify-v1-phase5-evidence.sh"
        with tempfile.TemporaryDirectory(prefix="phase5-path-") as path_temp:
            path_root = Path(path_temp)
            git_path = shutil.which("git")
            check(git_path is not None, "git is unavailable for missing-rg test")
            os.symlink(git_path, path_root / "git")
            os.symlink(sys.executable, path_root / "python3")
            completed = run(["/bin/bash", str(wrapper_path), "--dogfood-only"], expected=1, environment={"PATH": str(path_root)})
            check(b"requires: rg" in completed.stderr, "wrapper did not fail deterministically when rg was missing")
            NEGATIVE_COUNT += 1
        check(NEGATIVE_COUNT == 25, f"adversarial suite count changed: {NEGATIVE_COUNT}")


def validate_story_packet() -> None:
    story = ROOT / "docs" / "stories" / "US-110-v1-dogfood-pilot-baselines"
    for name in ["overview.md", "design.md", "execplan.md", "validation.md"]:
        check((story / name).is_file() and (story / name).stat().st_size > 0, f"US-110 packet file missing: {name}")
    content = "\n".join((story / name).read_text(encoding="utf-8") for name in ["overview.md", "design.md", "execplan.md", "validation.md"])
    check("ssh-ed25519" in content and "packet manifest" in content.lower(), "US-110 does not describe corrected authentication/custody proof")
    check("Phase 5 is not accepted" in content and "Phase 6 remains" in content, "US-110 opened a later phase")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-pilot-baselines", action="store_true")
    parser.add_argument("--dogfood-only", action="store_true")
    arguments = parser.parse_args()
    proof("Repository Harness paths and exact ordinary-task argv remain path-stable and core-command-free", validate_dogfood)
    if arguments.dogfood_only:
        print("V1 Phase 5 Repository Harness dogfood verification passed (1 proof group)")
        return
    catalog_digest, cards = validate_catalog()
    index, _ = load_evidence_index(EVIDENCE)
    proof("Draft 2020-12 contracts, fixed P0-P7 catalog, trusted-owner registry, and candidate index validate", lambda: None)
    proof("ephemeral test owner authenticates a complete manifest and resolvable repository bundle with SSH Ed25519", prove_positive_packet)
    proof("25 adversarial oracle, custody, timeline, environment, subprocess, and completeness cases fail closed", prove_negative_contracts)
    proof("US-110 documents only corrected repository-owned candidate proof", validate_story_packet)
    if index["status"] == "complete":
        proof("default verifier automatically loads two complete live pilot packets", lambda: verify_index_mode(index, EVIDENCE, catalog_digest, cards, require_live=False))
    elif arguments.require_pilot_baselines:
        try:
            verify_index_mode(index, EVIDENCE, catalog_digest, cards, require_live=True)
        except VerificationError as error:
            print(f"V1 Phase 5 live pilot evidence blocked: {error}", file=sys.stderr)
            for blocker in index["blockers"]:
                print(f"- {blocker}", file=sys.stderr)
            raise SystemExit(2) from error
    print(f"V1 Phase 5 candidate verification passed ({PASS_COUNT} executable proof groups)")


if __name__ == "__main__":
    try:
        main()
    except VerificationError as error:
        print(f"V1 Phase 5 candidate verification failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

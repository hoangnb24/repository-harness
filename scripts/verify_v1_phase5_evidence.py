#!/usr/bin/env python3
"""Fail-closed Phase 5 dogfood and authenticated pilot-baseline verifier."""

from __future__ import annotations

import argparse
import base64
import binascii
from collections import defaultdict
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
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
EXECUTABLE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
HOSTNAME = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$"
)
NAMESPACE = "repository-harness-phase5"
MAX_TRUSTED_OWNER_REGISTRY_BYTES = 1024 * 1024
PHASE5_ACCEPTED_COMMIT = "5d6e6bc516cd60e47c60ae3b516363cd99b433a5"
CORE_PACKET_FILES = {
    "enrollment.json", "environment.json", "eligibility.json",
    "interventions.json", "baseline-result.json", "repository.bundle",
}
ORDINARY_ARGV = [
    ["rg", "--no-config", "-q", "Phases 1-5 accepted at the authenticated baseline gate", "docs/stories/US-105-harness-v1-implementation/overview.md"],
    ["rg", "--no-config", "-q", "Phase 6 remains not started", "docs/stories/US-105-harness-v1-implementation/validation.md"],
    ["git", "--no-optional-locks", "diff", "--no-ext-diff", "--check"],
]
CURRENT_PHASE_BOUNDARY_ARGV = [
    ["rg", "--no-config", "-q", "Framework implemented and verified; live P0-P7 validation pending;", "docs/stories/US-111-v1-phase6-capability-evaluation/validation.md"],
    ["rg", "--no-config", "-q", "Phase 6 not accepted", "docs/stories/US-111-v1-phase6-capability-evaluation/validation.md"],
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
    hostname = parsed.hostname
    check(not hostname.endswith(".") and HOSTNAME.fullmatch(hostname) is not None, "repository identity contains an ambiguous hostname")
    check(not parsed.query and not parsed.fragment and not parsed.path.endswith("/"), "repository identity contains query, fragment, or trailing slash")
    check("%" not in value and "\\" not in value, "repository identity contains encoded or ambiguous syntax")
    raw_segments = parsed.path.split("/")
    check(
        parsed.path.startswith("/")
        and len(raw_segments) > 1
        and raw_segments[0] == ""
        and all(segment and segment not in {".", ".."} for segment in raw_segments[1:]),
        "repository identity contains raw dot, dot-dot, or empty path segments",
    )
    parts = PurePosixPath(parsed.path).parts
    check(parts and parts[-1].endswith(".git") and all(part not in {".", ".."} for part in parts), "repository identity must end in an unambiguous .git path")
    canonical_hostname = hostname.lower()
    if canonical_hostname == "www.github.com":
        canonical_hostname = "github.com"
    canonical_path = parsed.path.lower() if canonical_hostname == "github.com" else parsed.path
    normalized = f"https://{canonical_hostname}{canonical_path}"
    check(value == normalized, "repository identity is not canonical")
    return normalized


def signing_key_fingerprint(public_key: str) -> str:
    parts = public_key.split(" ")
    check(len(parts) == 2 and parts[0] == "ssh-ed25519", "trusted owner key is not canonical SSH Ed25519")
    try:
        key_blob = base64.b64decode(parts[1], validate=True)
    except (ValueError, binascii.Error) as error:
        raise VerificationError("trusted owner key is malformed") from error
    check(base64.b64encode(key_blob).decode("ascii") == parts[1], "trusted owner key encoding is not canonical")
    fingerprint = base64.b64encode(hashlib.sha256(key_blob).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{fingerprint}"


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
        arguments = entry["argv"]
        if arguments[0] == "rg":
            historical = run(
                ["git", "show", f"{PHASE5_ACCEPTED_COMMIT}:{arguments[-1]}"],
            ).stdout
            completed = run(
                arguments[:-1] + ["-"],
                input_bytes=historical,
                expected=entry["exit_code"],
            )
        else:
            completed = run(arguments, expected=entry["exit_code"])
        check(completed.returncode == 0, f"ordinary task check failed: {entry['argv']}")
    for arguments in CURRENT_PHASE_BOUNDARY_ARGV:
        run(arguments)


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
    check(all(EXECUTABLE_TOKEN.fullmatch(name) is not None for name in tools), "versioned tool names must be canonical bare executable tokens")
    enabled = document["enabled_tools"]
    check(len(enabled) == len(set(enabled)) and set(enabled) <= set(tools), "enabled tools are duplicated or absent from versioned tools")
    exact_cards(document["acceptance_commands"], "environment acceptance commands")
    for fixture in document["fixtures"]:
        check(artifact_digests.get(fixture["path"]) == fixture["sha256"], f"fixture is outside authenticated custody or has wrong digest: {fixture['path']}")


def validate_acceptance_tools(environment: dict[str, Any], eligibility: dict[str, Any]) -> None:
    tools = [tool["name"] for tool in environment["tools"]]
    enabled = set(environment["enabled_tools"])
    applicable = {card["card_id"] for card in eligibility["cards"] if card["disposition"] == "eligible"}
    for command in environment["acceptance_commands"]:
        if command["card_id"] not in applicable:
            continue
        executable = command["argv"][0]
        check(EXECUTABLE_TOKEN.fullmatch(executable) is not None, f"{command['card_id']} acceptance executable is not a canonical bare token")
        check(tools.count(executable) == 1, f"{command['card_id']} acceptance executable does not resolve to exactly one versioned tool")
        check(executable in enabled, f"{command['card_id']} acceptance executable is not enabled")


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


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        check(key not in document, f"trusted-owner registry contains duplicate JSON key: {key}")
        document[key] = value
    return document


def parse_trusted_owners_bytes(
    payload: bytes, location: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    try:
        document = json.loads(
            payload.decode("utf-8"), object_pairs_hook=reject_duplicate_json_keys
        )
    except VerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot parse {location}: {error}") from error
    validate(document, schema("trusted-owners"), location)
    owners: dict[str, dict[str, Any]] = {}
    repositories: set[str] = set()
    fingerprint_scopes: dict[str, dict[str, Any]] = {}
    for owner in document["owners"]:
        owner_id = owner["owner_id"]
        owner_identity = owner["owner_identity"]
        check(owner_id not in owners, f"repository-scoped trusted owner ID is duplicated: {owner_id}")
        repository = canonical_repository(owner["canonical_repository"])
        check(repository not in repositories, f"trusted owner repository scope is duplicated: {repository}")
        fingerprint = signing_key_fingerprint(owner["public_key"])
        prior_scope = fingerprint_scopes.get(fingerprint)
        if prior_scope is not None:
            check(
                prior_scope["owner_identity"] == owner_identity,
                f"trusted owner signing key is reused across stable owner identities: {fingerprint}",
            )
            check(
                repository not in prior_scope["repositories"],
                f"trusted owner signing key is reused within one repository scope: {fingerprint}",
            )
        parse_time(owner["trusted_at"], "trusted owner time")
        owners[owner_id] = {**owner, "signing_key_fingerprint": fingerprint}
        repositories.add(repository)
        if prior_scope is None:
            fingerprint_scopes[fingerprint] = {
                "owner_identity": owner_identity,
                "repositories": {repository},
            }
        else:
            prior_scope["repositories"].add(repository)
    return document, owners


def parse_trusted_owners(
    path: Path, location: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise VerificationError(f"cannot read {location}: {error}") from error
    check(
        len(payload) <= MAX_TRUSTED_OWNER_REGISTRY_BYTES,
        f"{location} exceeds the bounded registry size",
    )
    return parse_trusted_owners_bytes(payload, location)


def validate_tracked_trust_placeholder(evidence_root: Path) -> None:
    path = contained_member(evidence_root, "trusted-owners.json", "tracked trust placeholder")
    document, _ = parse_trusted_owners(path, "tracked trust placeholder")
    check(not document["owners"], "tracked trusted-owners placeholder must remain empty and cannot authorize live pilots")


def load_external_trusted_owners(path: Path | None, expected_sha256: str | None) -> tuple[dict[str, dict[str, Any]], str]:
    check(path is not None and expected_sha256 is not None, "complete live evidence requires --trusted-owner-registry and --trusted-owner-registry-sha256")
    check(SHA256.fullmatch(expected_sha256) is not None, "external trusted-owner registry digest is malformed")
    check(path.is_absolute(), "external trusted-owner registry path must be absolute")
    try:
        initial_stat = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise VerificationError(f"external trusted-owner registry is unavailable: {path}") from error
    check(
        not path.is_symlink() and stat.S_ISREG(initial_stat.st_mode),
        "external trusted-owner registry must be a regular non-symlink file",
    )
    try:
        resolved.relative_to(ROOT.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise VerificationError("external trusted-owner registry must be supplied from outside the candidate repository")
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise VerificationError(f"cannot open external trusted-owner registry: {path}") from error
    try:
        opened_stat = os.fstat(descriptor)
        check(
            stat.S_ISREG(opened_stat.st_mode),
            "external trusted-owner registry descriptor is not a regular file",
        )
        check(
            (opened_stat.st_dev, opened_stat.st_ino)
            == (initial_stat.st_dev, initial_stat.st_ino),
            "external trusted-owner registry changed before its single open",
        )
        with os.fdopen(descriptor, "rb", closefd=True) as registry:
            descriptor = -1
            payload = registry.read(MAX_TRUSTED_OWNER_REGISTRY_BYTES + 1)
    except OSError as error:
        raise VerificationError(f"cannot read external trusted-owner registry: {path}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    check(
        len(payload) <= MAX_TRUSTED_OWNER_REGISTRY_BYTES,
        "external trusted-owner registry exceeds the bounded registry size",
    )
    digest = sha256_bytes(payload)
    check(digest == expected_sha256, "external trusted-owner registry digest mismatch")
    _, owners = parse_trusted_owners_bytes(payload, "external trusted-owner registry")
    check(owners, "external trusted-owner registry contains no authorized owners")
    return owners, digest


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
    check(owner_id in trusted, "packet owner is absent from the caller-supplied external trust registry")
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
    validate_acceptance_tools(environment, eligibility)
    validate_interventions(interventions)
    validate_baseline(baseline, artifact_digests)
    owner = verify_owner_authentication(authentication, trusted)
    statement = authentication["statement"]
    repository = canonical_repository(enrollment["canonical_repository"])
    check(repository == canonical_repository(owner["canonical_repository"]) == statement["canonical_repository"], "repository identity differs across external trust, enrollment, and authentication")
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
    bundle_digest = artifact_digests[bundle_path]
    check(statement["repository_bundle_sha256"] == bundle_digest, "authenticated repository-bundle digest mismatch")
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
            if disposition["disposition"] == "eligible" and "environment digest" in item["requirement"].casefold():
                artifact = contained_member(packet_dir, item["artifact"], f"{card_id} environment-digest evidence")
                try:
                    payload = artifact.read_bytes()
                except OSError as error:
                    raise VerificationError(f"cannot read {card_id} environment-digest evidence: {item['artifact']}") from error
                check(
                    environment["environment_sha256"].encode("ascii") in payload,
                    f"{card_id} environment-digest evidence does not contain the canonical packet environment digest: {item['artifact']}",
                )
    validate_timeline(enrollment, environment, eligibility, interventions, baseline, statement, owner)
    return {
        "pilot_id": pilot_id,
        "repository": repository,
        "owner_id": owner["owner_id"],
        "owner_identity": owner["owner_identity"],
        "signing_key_fingerprint": owner["signing_key_fingerprint"],
        "repository_bundle_sha256": bundle_digest,
    }


def validate_pilot_independence(packets: list[dict[str, Any]]) -> None:
    repositories = [packet["repository"] for packet in packets]
    owner_ids = [packet["owner_id"] for packet in packets]
    repository_bundles = [packet["repository_bundle_sha256"] for packet in packets]
    check(len(repositories) == len(set(repositories)), "pilots reuse the same canonical repository")
    check(len(owner_ids) == len(set(owner_ids)), "pilots reuse the same repository-scoped owner ID")
    check(len(repository_bundles) == len(set(repository_bundles)), "pilots reuse the same authenticated repository bundle")
    fingerprint_identities: dict[str, str] = {}
    for packet in packets:
        fingerprint = packet["signing_key_fingerprint"]
        identity = packet["owner_identity"]
        prior_identity = fingerprint_identities.get(fingerprint)
        if prior_identity is None:
            fingerprint_identities[fingerprint] = identity
        else:
            check(
                prior_identity == identity,
                "pilots reuse one signing-key fingerprint across different stable owner identities",
            )


def load_evidence_index(evidence_root: Path) -> dict[str, Any]:
    index = load_json(contained_member(evidence_root, "index.json", "evidence index"))
    validate(index, schema("evidence-index"), "evidence index")
    check(len(index["pilots"]) == len(set(index["pilots"])), "evidence index duplicates a pilot")
    validate_tracked_trust_placeholder(evidence_root)
    if index["status"] == "candidate-awaiting-pilot-authorization":
        check(not index["pilots"] and index["blockers"], "candidate evidence index hides pilots or blockers")
    else:
        check(len(index["pilots"]) >= 2 and not index["blockers"], "complete evidence index is shallow or contradictory")
    return index


def require_live_evidence(
    evidence_root: Path, catalog_digest: str, cards: dict[str, dict[str, Any]],
    trusted_owner_registry: Path | None, trusted_owner_registry_sha256: str | None,
) -> None:
    index = load_evidence_index(evidence_root)
    check(index["status"] == "complete", "Phase 5 evidence index is not complete")
    owners, _ = load_external_trusted_owners(trusted_owner_registry, trusted_owner_registry_sha256)
    packets = []
    for pilot_id in index["pilots"]:
        relative_name(pilot_id, "pilot directory")
        packet_dir = contained_member(evidence_root, pilot_id, "pilot directory", directory=True)
        packets.append(validate_packet(packet_dir, pilot_id, owners, catalog_digest, cards))
    validate_pilot_independence(packets)


def verify_index_mode(
    index: dict[str, Any], evidence_root: Path, catalog_digest: str,
    cards: dict[str, dict[str, Any]], *, require_live: bool,
    trusted_owner_registry: Path | None = None,
    trusted_owner_registry_sha256: str | None = None,
) -> bool:
    if index["status"] == "complete" or require_live:
        require_live_evidence(
            evidence_root, catalog_digest, cards,
            trusted_owner_registry, trusted_owner_registry_sha256,
        )
        return True
    return False


def make_git_bundle(root: Path, fixture_label: str = "a") -> tuple[Path, str]:
    root.mkdir(parents=True)
    repository = root / "source"
    repository.mkdir()
    run(["git", "init", str(repository)])
    (repository / "README.md").write_text(
        f"synthetic authenticated pilot fixture {fixture_label}\n", encoding="utf-8",
    )
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
            content = f"synthetic evidence for {card_id}: {requirement}\n"
            if "environment digest" in requirement.casefold():
                content += f"canonical packet environment digest: {environment['environment_sha256']}\n"
            path.write_text(content, encoding="utf-8")
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
        "repository_bundle_sha256": sha256_file(packet / "repository.bundle"),
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
            "signing_key_fingerprint": signing_key_fingerprint(public_key),
        }
    }
    return packet, trusted, key, cards, catalog_digest


def external_registry_document(trusted: dict[str, dict[str, Any]]) -> dict[str, Any]:
    owners = []
    for owner in trusted.values():
        owners.append({key: value for key, value in owner.items() if key != "signing_key_fingerprint"})
    return {"schema": "repository-harness-trusted-pilot-owners/v1", "owners": owners}


def build_repository_scoped_packet(
    source: Path, destination: Path, key: Path, source_owner: dict[str, Any], *,
    owner_identity: str, distinct_bundle: bool,
) -> dict[str, Any]:
    """Build a second repository authorization under one existing signing key."""
    shutil.copytree(source, destination)
    pilot_id = "synthetic-pilot-b"
    owner_id = "synthetic-owner-b"
    repository = "https://example.test/synthetic-b.git"
    authorization_scope = "synthetic repository-scoped verifier fixture"

    revision: str | None = None
    if distinct_bundle:
        bundle, revision = make_git_bundle(destination.parent / "git-evidence-b", "b")
        shutil.copyfile(bundle, destination / "repository.bundle")

    enrollment = load_json(destination / "enrollment.json")
    enrollment.update({
        "pilot_id": pilot_id, "canonical_repository": repository,
        "owner_id": owner_id, "authorization_scope": authorization_scope,
    })
    if revision is not None:
        enrollment["starting_revision"]["value"] = revision
    environment = load_json(destination / "environment.json")
    prior_environment_digest = environment["environment_sha256"]
    environment["pilot_id"] = pilot_id
    environment["environment_sha256"] = canonical_digest(environment, "environment_sha256")
    eligibility = load_json(destination / "eligibility.json")
    eligibility["pilot_id"] = pilot_id
    interventions = load_json(destination / "interventions.json")
    interventions["pilot_id"] = pilot_id
    for name, document in [
        ("enrollment.json", enrollment), ("environment.json", environment),
        ("eligibility.json", eligibility), ("interventions.json", interventions),
    ]:
        write_json(destination / name, document)
    baseline = load_json(destination / "baseline-result.json")
    baseline["pilot_id"] = pilot_id
    if revision is not None:
        baseline["starting_revision"] = revision
    baseline["environment_sha256"] = environment["environment_sha256"]
    baseline["intervention_log_sha256"] = sha256_file(destination / "interventions.json")
    for result in baseline["cards"]:
        for evidence in result["evidence"]:
            if "environment digest" not in evidence["requirement"].casefold():
                continue
            artifact_path = destination / evidence["artifact"]
            payload = artifact_path.read_bytes()
            check(prior_environment_digest.encode("ascii") in payload, "synthetic environment-digest fixture lost its source binding")
            artifact_path.write_bytes(payload.replace(
                prior_environment_digest.encode("ascii"),
                environment["environment_sha256"].encode("ascii"),
            ))
    baseline["result_sha256"] = canonical_digest(baseline, "result_sha256")
    write_json(destination / "baseline-result.json", baseline)

    manifest = load_json(destination / "packet-manifest.json")
    manifest["pilot_id"] = pilot_id
    manifest["custody_id"] = "synthetic-pilot-b-custody-1"
    for artifact in manifest["artifacts"]:
        artifact["sha256"] = sha256_file(destination / artifact["path"])
    write_json(destination / "packet-manifest.json", manifest)
    authentication = load_json(destination / "authentication.json")
    authentication["owner_id"] = owner_id
    statement = authentication["statement"]
    statement.update({
        "pilot_id": pilot_id, "canonical_repository": repository,
        "owner_id": owner_id, "authorization_scope": authorization_scope,
        "starting_revision": enrollment["starting_revision"]["value"],
        "repository_bundle_sha256": sha256_file(destination / "repository.bundle"),
        "packet_manifest_sha256": sha256_file(destination / "packet-manifest.json"),
        "publication_id": "synthetic-pilot-b-baseline-publication-1",
        "custody_id": manifest["custody_id"],
    })
    authentication["signature"] = sign_statement(key, statement)
    write_json(destination / "authentication.json", authentication)
    return {
        "owner_id": owner_id,
        "owner_identity": owner_identity,
        "canonical_repository": repository,
        "authorization_scope": authorization_scope,
        "public_key": source_owner["public_key"],
        "trust_source": "synthetic repository-scoped verifier fixture",
        "trusted_at": source_owner["trusted_at"],
        "signing_key_fingerprint": source_owner["signing_key_fingerprint"],
    }


def rewrite_packet_repository(packet: Path, key: Path, repository: str) -> None:
    """Re-sign a complete synthetic packet after changing its repository scope."""
    enrollment = load_json(packet / "enrollment.json")
    enrollment["canonical_repository"] = repository
    write_json(packet / "enrollment.json", enrollment)

    manifest = load_json(packet / "packet-manifest.json")
    next(artifact for artifact in manifest["artifacts"] if artifact["path"] == "enrollment.json")["sha256"] = sha256_file(packet / "enrollment.json")
    write_json(packet / "packet-manifest.json", manifest)

    authentication = load_json(packet / "authentication.json")
    authentication["statement"]["canonical_repository"] = repository
    authentication["statement"]["packet_manifest_sha256"] = sha256_file(packet / "packet-manifest.json")
    authentication["signature"] = sign_statement(key, authentication["statement"])
    write_json(packet / "authentication.json", authentication)


def rebind_authenticated_artifact(packet: Path, key: Path, relative: str, payload: bytes) -> None:
    """Rewrite one synthetic artifact and fully renew its manifest and signature."""
    artifact_path = contained_member(packet, relative, "synthetic rebound artifact")
    artifact_path.write_bytes(payload)

    manifest_path = packet / "packet-manifest.json"
    manifest = load_json(manifest_path)
    entry = next((item for item in manifest["artifacts"] if item["path"] == relative), None)
    check(entry is not None, "synthetic rebound artifact is absent from the packet manifest")
    entry["sha256"] = sha256_file(artifact_path)
    write_json(manifest_path, manifest)

    authentication_path = packet / "authentication.json"
    authentication = load_json(authentication_path)
    authentication["statement"]["packet_manifest_sha256"] = sha256_file(manifest_path)
    authentication["signature"] = sign_statement(key, authentication["statement"])
    write_json(authentication_path, authentication)


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
        root = Path(temporary)
        evidence = root / "evidence"
        packet_a, trusted, key, cards, catalog_digest = build_synthetic_packet(evidence)
        owner_a = trusted[next(iter(trusted))]
        packet_b = evidence / "synthetic-pilot-b"
        owner_b = build_repository_scoped_packet(
            packet_a, packet_b, key, owner_a,
            owner_identity=owner_a["owner_identity"], distinct_bundle=True,
        )
        trusted[owner_b["owner_id"]] = owner_b
        registry = root / "external-trusted-owners.json"
        write_json(registry, external_registry_document(trusted))
        loaded, _ = load_external_trusted_owners(registry, sha256_file(registry))
        packets = [
            validate_packet(packet_a, packet_a.name, loaded, catalog_digest, cards),
            validate_packet(packet_b, packet_b.name, loaded, catalog_digest, cards),
        ]
        validate_pilot_independence(packets)


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
        undeclared_command = load_json(packet / "environment.json")
        undeclared_command["acceptance_commands"][0]["argv"][0] = "undeclared-tool"
        expect_rejection(
            "acceptance executable absent from versioned/enabled tools",
            lambda: validate_acceptance_tools(undeclared_command, load_json(packet / "eligibility.json")),
        )
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

        stale_root = root / "stale-environment-digest"
        stale_packet, stale_trusted, stale_key, stale_cards, stale_catalog = build_synthetic_packet(stale_root)
        stale_baseline = load_json(stale_packet / "baseline-result.json")
        stale_item = next(
            item
            for result in stale_baseline["cards"]
            for item in result["evidence"]
            if "environment digest" in item["requirement"].casefold()
        )
        stale_digest = sha256_bytes(b"synthetic legacy trailing-newline environment")
        check(stale_digest != load_json(stale_packet / "environment.json")["environment_sha256"], "stale digest fixture collided with the current environment")
        rebind_authenticated_artifact(
            stale_packet, stale_key, stale_item["artifact"],
            f"source-run legacy trailing-newline environment digest: {stale_digest}\n".encode("utf-8"),
        )
        expect_rejection(
            "fully rebound and re-signed environment-digest evidence contains only a stale digest",
            lambda: validate_packet(stale_packet, stale_packet.name, stale_trusted, stale_catalog, stale_cards),
        )

        omitted_root = root / "omitted-environment-digest"
        omitted_packet, omitted_trusted, omitted_key, omitted_cards, omitted_catalog = build_synthetic_packet(omitted_root)
        omitted_baseline = load_json(omitted_packet / "baseline-result.json")
        omitted_item = next(
            item
            for result in omitted_baseline["cards"]
            for item in result["evidence"]
            if "environment digest" in item["requirement"].casefold()
        )
        rebind_authenticated_artifact(
            omitted_packet, omitted_key, omitted_item["artifact"],
            b"authenticated evidence intentionally omits the required binding\n",
        )
        expect_rejection(
            "fully rebound and re-signed environment-digest evidence omits the digest",
            lambda: validate_packet(omitted_packet, omitted_packet.name, omitted_trusted, omitted_catalog, omitted_cards),
        )

        expect_rejection("absolute evidence path", lambda: relative_name("/tmp/evidence", "artifact"))
        expect_rejection("parent traversal", lambda: relative_name("../evidence", "artifact"))
        symlink = packet / "artifacts" / "escape"
        try:
            symlink.symlink_to(packet / "enrollment.json")
            expect_rejection("symlink escape", lambda: contained_member(packet, "artifacts/escape", "artifact"))
        finally:
            symlink.unlink(missing_ok=True)
        expect_rejection("mismatched pilot directory", lambda: validate_packet(packet, "another-pilot", trusted, catalog_digest, cards))

        identity = {
            "pilot_id": "a", "repository": enrollment["canonical_repository"],
            "owner_id": "owner-a", "owner_identity": "person-a",
            "signing_key_fingerprint": "SHA256:key-a", "repository_bundle_sha256": "a" * 64,
        }
        independent = {
            "pilot_id": "b", "repository": "https://example.test/synthetic-b.git",
            "owner_id": "owner-b", "owner_identity": "person-b",
            "signing_key_fingerprint": "SHA256:key-b", "repository_bundle_sha256": "b" * 64,
        }
        same_repository = {**independent, "repository": identity["repository"]}
        same_owner_id = {**independent, "owner_id": identity["owner_id"], "owner_identity": identity["owner_identity"]}
        same_signing_key = {**independent, "signing_key_fingerprint": identity["signing_key_fingerprint"]}
        same_bundle = {**independent, "repository_bundle_sha256": identity["repository_bundle_sha256"]}
        expect_rejection("same repository dual pilots", lambda: validate_pilot_independence([identity, same_repository]))
        expect_rejection("same repository-scoped owner ID dual pilots", lambda: validate_pilot_independence([identity, same_owner_id]))
        expect_rejection("same signing key across different stable identities", lambda: validate_pilot_independence([identity, same_signing_key]))
        expect_rejection("same repository bundle dual pilots", lambda: validate_pilot_independence([identity, same_bundle]))

        alias_root = root / "one-key-one-bundle-attack"
        alias_evidence = alias_root / "evidence"
        packet_a, alias_trusted, alias_key, alias_cards, alias_catalog = build_synthetic_packet(alias_evidence)
        owner_a = alias_trusted[next(iter(alias_trusted))]
        packet_b = alias_evidence / "synthetic-pilot-b"
        owner_b = build_repository_scoped_packet(
            packet_a, packet_b, alias_key, owner_a,
            owner_identity=owner_a["owner_identity"], distinct_bundle=False,
        )
        alias_trusted[owner_b["owner_id"]] = owner_b
        aliased_packets = [
            validate_packet(packet_a, packet_a.name, {owner_a["owner_id"]: owner_a}, alias_catalog, alias_cards),
            validate_packet(packet_b, packet_b.name, {owner_b["owner_id"]: owner_b}, alias_catalog, alias_cards),
        ]
        expect_rejection(
            "same-owner one-key one-bundle two-repository packet construction",
            lambda: validate_pilot_independence(aliased_packets),
        )
        write_json(alias_evidence / "trusted-owners.json", {"schema": "repository-harness-trusted-pilot-owners/v1", "owners": []})
        write_json(alias_evidence / "index.json", {
            "schema": "repository-harness-phase5-evidence-index/v2", "phase": 5, "status": "complete",
            "card_catalog": "cards/catalog.json", "trusted_owners": "trusted-owners.json",
            "pilots": [packet_a.name, packet_b.name], "blockers": [],
        })
        alias_registry = alias_root / "external-trusted-owners.json"
        write_json(alias_registry, external_registry_document(alias_trusted))
        alias_index = load_json(alias_evidence / "index.json")
        expect_rejection(
            "same-owner one-key one-bundle complete live index",
            lambda: verify_index_mode(
                alias_index, alias_evidence, alias_catalog, alias_cards, require_live=False,
                trusted_owner_registry=alias_registry,
                trusted_owner_registry_sha256=sha256_file(alias_registry),
            ),
        )

        different_identity_registry = alias_root / "different-identity-trust.json"
        different_identity_owner = {**owner_b, "owner_identity": "synthetic-independent-owner-b"}
        write_json(
            different_identity_registry,
            external_registry_document({
                owner_a["owner_id"]: owner_a,
                different_identity_owner["owner_id"]: different_identity_owner,
            }),
        )
        expect_rejection(
            "one signing key claimed by different stable owner identities",
            lambda: parse_trusted_owners(different_identity_registry, "different-identity trust fixture"),
        )

        duplicate_scope_registry = alias_root / "duplicate-scope-trust.json"
        duplicate_scope_owner = {**owner_b, "canonical_repository": owner_a["canonical_repository"]}
        write_json(
            duplicate_scope_registry,
            external_registry_document({
                owner_a["owner_id"]: owner_a,
                duplicate_scope_owner["owner_id"]: duplicate_scope_owner,
            }),
        )
        expect_rejection(
            "two repository-scoped owner IDs claim one canonical repository",
            lambda: parse_trusted_owners(duplicate_scope_registry, "duplicate-scope trust fixture"),
        )

        repository_alias_root = root / "repository-alias-attack"
        repository_alias_evidence = repository_alias_root / "evidence"
        alias_packet_a, repository_alias_trusted, repository_alias_key, repository_alias_cards, repository_alias_catalog = build_synthetic_packet(repository_alias_evidence)
        repository_alias_owner_a = repository_alias_trusted[next(iter(repository_alias_trusted))]
        alias_packet_b = repository_alias_evidence / "synthetic-pilot-b"
        repository_alias_owner_b = build_repository_scoped_packet(
            alias_packet_a, alias_packet_b, repository_alias_key, repository_alias_owner_a,
            owner_identity=repository_alias_owner_a["owner_identity"], distinct_bundle=True,
        )
        write_json(repository_alias_evidence / "trusted-owners.json", {
            "schema": "repository-harness-trusted-pilot-owners/v1", "owners": [],
        })
        write_json(repository_alias_evidence / "index.json", {
            "schema": "repository-harness-phase5-evidence-index/v2", "phase": 5, "status": "complete",
            "card_catalog": "cards/catalog.json", "trusted_owners": "trusted-owners.json",
            "pilots": [alias_packet_a.name, alias_packet_b.name], "blockers": [],
        })
        repository_alias_index = load_json(repository_alias_evidence / "index.json")
        repository_alias_registry = repository_alias_root / "external-trusted-owners.json"

        def reject_repository_alias(repository: str, label: str) -> None:
            aliased_owner_b = {**repository_alias_owner_b, "canonical_repository": repository}
            aliased_trusted = {
                repository_alias_owner_a["owner_id"]: repository_alias_owner_a,
                aliased_owner_b["owner_id"]: aliased_owner_b,
            }
            write_json(repository_alias_registry, external_registry_document(aliased_trusted))
            expect_rejection(
                f"{label} in external trusted-owner registry",
                lambda: parse_trusted_owners(repository_alias_registry, f"{label} trust fixture"),
            )
            rewrite_packet_repository(alias_packet_b, repository_alias_key, repository)
            expect_rejection(
                f"{label} in complete signed live index",
                lambda: verify_index_mode(
                    repository_alias_index, repository_alias_evidence,
                    repository_alias_catalog, repository_alias_cards, require_live=False,
                    trusted_owner_registry=repository_alias_registry,
                    trusted_owner_registry_sha256=sha256_file(repository_alias_registry),
                ),
            )

        reject_repository_alias("https://example.test/./synthetic-a.git", "raw dot-segment repository alias")
        reject_repository_alias("https://example.test./synthetic-a.git", "trailing-host-dot repository alias")

        github_repository = "https://github.com/synthetic-owner/synthetic-a.git"
        github_alias = "https://github.com/SYNTHETIC-OWNER/SYNTHETIC-A.git"
        rewrite_packet_repository(alias_packet_a, repository_alias_key, github_repository)
        github_owner_a = {**repository_alias_owner_a, "canonical_repository": github_repository}
        github_owner_b = {**repository_alias_owner_b, "canonical_repository": github_alias}
        github_trusted = {
            github_owner_a["owner_id"]: github_owner_a,
            github_owner_b["owner_id"]: github_owner_b,
        }
        write_json(repository_alias_registry, external_registry_document(github_trusted))
        expect_rejection(
            "GitHub path-case repository alias in external trusted-owner registry",
            lambda: parse_trusted_owners(repository_alias_registry, "GitHub path-case alias trust fixture"),
        )
        rewrite_packet_repository(alias_packet_b, repository_alias_key, github_alias)
        expect_rejection(
            "GitHub path-case repository alias in complete signed live index",
            lambda: verify_index_mode(
                repository_alias_index, repository_alias_evidence,
                repository_alias_catalog, repository_alias_cards, require_live=False,
                trusted_owner_registry=repository_alias_registry,
                trusted_owner_registry_sha256=sha256_file(repository_alias_registry),
            ),
        )

        github_hostname_alias = "https://www.github.com/synthetic-owner/synthetic-a.git"
        github_hostname_owner_b = {
            **repository_alias_owner_b,
            "canonical_repository": github_hostname_alias,
        }
        github_hostname_trusted = {
            github_owner_a["owner_id"]: github_owner_a,
            github_hostname_owner_b["owner_id"]: github_hostname_owner_b,
        }
        write_json(repository_alias_registry, external_registry_document(github_hostname_trusted))
        expect_rejection(
            "GitHub www-host repository alias in external trusted-owner registry",
            lambda: parse_trusted_owners(repository_alias_registry, "GitHub www-host alias trust fixture"),
        )
        rewrite_packet_repository(alias_packet_b, repository_alias_key, github_hostname_alias)
        expect_rejection(
            "GitHub www-host repository alias in complete signed live index",
            lambda: verify_index_mode(
                repository_alias_index, repository_alias_evidence,
                repository_alias_catalog, repository_alias_cards, require_live=False,
                trusted_owner_registry=repository_alias_registry,
                trusted_owner_registry_sha256=sha256_file(repository_alias_registry),
            ),
        )
        expect_rejection(
            "raw dot-dot repository path segment",
            lambda: canonical_repository("https://example.test/scope/../synthetic-a.git"),
        )
        expect_rejection(
            "empty internal repository path segment",
            lambda: canonical_repository("https://example.test/scope//synthetic-a.git"),
        )

        shallow = root / "shallow-evidence"
        shallow.mkdir()
        write_json(shallow / "trusted-owners.json", {"schema": "repository-harness-trusted-pilot-owners/v1", "owners": []})
        write_json(shallow / "index.json", {"schema": "repository-harness-phase5-evidence-index/v2", "phase": 5, "status": "complete", "card_catalog": "cards/catalog.json", "trusted_owners": "trusted-owners.json", "pilots": ["pilot-a", "pilot-b"], "blockers": []})
        shallow_index = load_json(shallow / "index.json")
        expect_rejection("complete index without external trust through default dispatch", lambda: verify_index_mode(shallow_index, shallow, catalog_digest, cards, require_live=False))

        tracked_authority = root / "tracked-authority"
        tracked_authority.mkdir()
        write_json(tracked_authority / "trusted-owners.json", external_registry_document({owner_a["owner_id"]: owner_a}))
        write_json(tracked_authority / "index.json", {
            "schema": "repository-harness-phase5-evidence-index/v2", "phase": 5, "status": "complete",
            "card_catalog": "cards/catalog.json", "trusted_owners": "trusted-owners.json",
            "pilots": ["pilot-a", "pilot-b"], "blockers": [],
        })
        expect_rejection("tracked self-authorizing trust entry", lambda: load_evidence_index(tracked_authority))

        mismatched_registry = root / "mismatched-external-trust.json"
        write_json(mismatched_registry, external_registry_document(trusted))
        expect_rejection(
            "external trust registry digest mismatch",
            lambda: load_external_trusted_owners(mismatched_registry, "0" * 64),
        )

        duplicate_registry = root / "duplicate-key-external-trust.json"
        valid_registry_text = json.dumps(external_registry_document(trusted))
        duplicate_registry.write_text(
            valid_registry_text.replace(
                '"schema":',
                '"schema":"repository-harness-trusted-pilot-owners/v1","schema":',
                1,
            ),
            encoding="utf-8",
        )
        expect_rejection(
            "duplicate-key external trust registry",
            lambda: load_external_trusted_owners(
                duplicate_registry, sha256_file(duplicate_registry)
            ),
        )

        swapping_registry = root / "single-open-external-trust.json"
        replacement_registry = root / "single-open-replacement.json"
        write_json(swapping_registry, external_registry_document(trusted))
        write_json(
            replacement_registry,
            {
                "schema": "repository-harness-trusted-pilot-owners/v1",
                "owners": [],
            },
        )
        original_registry_payload = swapping_registry.read_bytes()
        original_registry_digest = sha256_bytes(original_registry_payload)
        original_sha256_bytes = sha256_bytes
        pathname_replaced = False

        def replace_pathname_after_hash(payload: bytes) -> str:
            nonlocal pathname_replaced
            digest = original_sha256_bytes(payload)
            if payload == original_registry_payload and not pathname_replaced:
                os.replace(replacement_registry, swapping_registry)
                pathname_replaced = True
            return digest

        globals()["sha256_bytes"] = replace_pathname_after_hash
        try:
            loaded_after_swap, _ = load_external_trusted_owners(
                swapping_registry, original_registry_digest
            )
        finally:
            globals()["sha256_bytes"] = original_sha256_bytes
        check(pathname_replaced, "atomic registry pathname substitution did not run")
        check(
            set(loaded_after_swap) == set(trusted),
            "atomic registry pathname substitution changed the parsed opened bytes",
        )
        NEGATIVE_COUNT += 1

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
        check(NEGATIVE_COUNT == 48, f"adversarial suite count changed: {NEGATIVE_COUNT}")


def validate_story_packet() -> None:
    story = ROOT / "docs" / "stories" / "US-110-v1-dogfood-pilot-baselines"
    for name in ["overview.md", "design.md", "execplan.md", "validation.md"]:
        check((story / name).is_file() and (story / name).stat().st_size > 0, f"US-110 packet file missing: {name}")
    content = "\n".join((story / name).read_text(encoding="utf-8") for name in ["overview.md", "design.md", "execplan.md", "validation.md"])
    normalized_content = " ".join(content.split())
    initiative = " ".join(
        " ".join(
            (ROOT / "docs" / "stories" / "US-105-harness-v1-implementation" / name)
            .read_text(encoding="utf-8")
            .split()
        )
        for name in ["overview.md", "design.md", "execplan.md", "validation.md"]
    )
    check("ssh-ed25519" in content and "packet manifest" in content.lower(), "US-110 does not describe corrected authentication/custody proof")
    check(
        "Phase 5 is accepted at the authenticated baseline gate" in normalized_content
        and "Phase 6 remains not started" in normalized_content,
        "US-110 does not preserve the accepted Phase 5 gate or opened a later phase",
    )
    check("docs commit awaits integration" not in initiative, "US-105 retains stale Phase 5 integration status")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-pilot-baselines", action="store_true")
    parser.add_argument("--dogfood-only", action="store_true")
    parser.add_argument("--trusted-owner-registry", type=Path)
    parser.add_argument("--trusted-owner-registry-sha256")
    arguments = parser.parse_args()
    proof("Repository Harness paths and exact ordinary-task argv remain path-stable and core-command-free", validate_dogfood)
    if arguments.dogfood_only:
        print("V1 Phase 5 Repository Harness dogfood verification passed (1 proof group)")
        return
    check(
        (arguments.trusted_owner_registry is None) == (arguments.trusted_owner_registry_sha256 is None),
        "--trusted-owner-registry and --trusted-owner-registry-sha256 must be supplied together",
    )
    catalog_digest, cards = validate_catalog()
    index = load_evidence_index(EVIDENCE)
    proof("Draft 2020-12 contracts, fixed P0-P7 catalog, empty tracked trust placeholder, and candidate index validate", lambda: None)
    proof("one stable owner and SSH Ed25519 key authenticate two repository-scoped packets with distinct repositories and bundles", prove_positive_packet)
    proof("48 adversarial oracle, trust, identity, custody, environment, subprocess, and completeness cases fail closed", prove_negative_contracts)
    proof("US-110 records accepted authenticated baselines and leaves Phase 6 closed", validate_story_packet)
    if index["status"] == "complete":
        proof(
            "default verifier automatically loads two complete live pilot packets",
            lambda: verify_index_mode(
                index, EVIDENCE, catalog_digest, cards, require_live=False,
                trusted_owner_registry=arguments.trusted_owner_registry,
                trusted_owner_registry_sha256=arguments.trusted_owner_registry_sha256,
            ),
        )
    elif arguments.require_pilot_baselines:
        try:
            verify_index_mode(
                index, EVIDENCE, catalog_digest, cards, require_live=True,
                trusted_owner_registry=arguments.trusted_owner_registry,
                trusted_owner_registry_sha256=arguments.trusted_owner_registry_sha256,
            )
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

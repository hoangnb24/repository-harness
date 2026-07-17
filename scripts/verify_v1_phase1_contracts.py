#!/usr/bin/env python3
"""Mechanical proof for Repository Harness V1 Phase 1 contracts."""

from __future__ import annotations

import base64
import binascii
import calendar
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import unicodedata
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "release" / "contracts" / "v1"
SCHEMAS = CONTRACT / "schemas"
FIXTURES = ROOT / "tests" / "fixtures" / "v1-phase1"
POS = FIXTURES / "positive"
NEG = FIXTURES / "negative"

WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
FORBIDDEN_FIELDS = {
    "task", "tasks", "run", "runs", "prompt", "prompts", "result", "results",
    "user", "users", "trace", "traces", "raw_command_output", "telemetry",
    "score", "scores", "scheduler", "schedule", "queue", "intake", "story",
    "backlog", "decision", "database", "sqlite", "changeset"
}

EXPECTED_CORE_COMMANDS = [
    {"name": "install", "mutation": "managed-files-and-manifest", "options": ["--preview", "--non-interactive", "--accept-preview-sha256", "--resume", "--rollback"], "exits": [0, 2, 3, 4, 64, 70, 74]},
    {"name": "update", "mutation": "managed-files-and-manifest", "options": ["--preview", "--non-interactive", "--accept-preview-sha256", "--resume", "--rollback"], "exits": [0, 2, 3, 4, 64, 70, 74]},
    {"name": "audit", "mutation": "none", "options": ["--json"], "exits": [0, 2, 3, 64, 70, 74]},
    {"name": "scaffold", "mutation": "one-explicit-neutral-artifact", "options": ["--template", "--destination", "--preview", "--non-interactive", "--accept-preview-sha256", "--resume", "--rollback"], "exits": [0, 3, 4, 64, 70, 74]},
    {"name": "status", "mutation": "none", "options": ["--json"], "exits": [0, 3, 64, 70, 74]},
    {"name": "version", "mutation": "none", "options": ["--json"], "exits": [0, 64, 70]},
]
EXPECTED_BRIDGE_COMMANDS = [
    {"name": "inspect", "mutation": "none", "options": ["--json"], "exits": [0, 3, 5, 64, 70, 74]},
    {"name": "export", "mutation": "new-export-and-archive-only", "options": ["--output", "--age-recipient", "--archive-plaintext", "--acknowledge-plaintext-recovery-risk"], "exits": [0, 3, 5, 64, 70, 74]},
    {"name": "preview", "mutation": "none", "options": ["--json"], "exits": [0, 2, 3, 4, 5, 64, 70, 74]},
    {"name": "apply", "mutation": "journal-owned-conversion", "options": ["--non-interactive", "--accept-preview-sha256", "--age-recipient", "--archive-plaintext", "--acknowledge-plaintext-recovery-risk"], "exits": [0, 2, 3, 4, 5, 64, 70, 74]},
    {"name": "resume", "mutation": "remaining-journal-operations", "options": ["--conversion-id"], "exits": [0, 2, 3, 4, 5, 64, 70, 74]},
    {"name": "rollback", "mutation": "matching-journal-owned-post-images", "options": ["--conversion-id"], "exits": [0, 3, 4, 5, 64, 70, 74]},
    {"name": "version", "mutation": "none", "options": ["--json"], "exits": [0, 64, 70]},
]
EXPECTED_RELEASE_PLATFORMS = [
    {"platform": "macos-arm64", "target": "aarch64-apple-darwin", "runner": "macos-15", "binary": "harness-cli-macos-arm64", "checksum": "harness-cli-macos-arm64.sha256"},
    {"platform": "macos-x64", "target": "x86_64-apple-darwin", "runner": "macos-15-intel", "binary": "harness-cli-macos-x64", "checksum": "harness-cli-macos-x64.sha256"},
    {"platform": "linux-x64", "target": "x86_64-unknown-linux-gnu", "runner": "ubuntu-24.04", "binary": "harness-cli-linux-x64", "checksum": "harness-cli-linux-x64.sha256"},
    {"platform": "linux-arm64", "target": "aarch64-unknown-linux-gnu", "runner": "ubuntu-24.04-arm", "binary": "harness-cli-linux-arm64", "checksum": "harness-cli-linux-arm64.sha256"},
    {"platform": "windows-x64", "target": "x86_64-pc-windows-msvc", "runner": "windows-latest", "binary": "harness-cli-windows-x64.exe", "checksum": "harness-cli-windows-x64.exe.sha256"},
]
PROMOTION_GATE_REQUIREMENTS = [
    "reserved-workflow-file-present",
    "repository-protection-evidence-binds-protected-workflow",
    "pinned-github-artifact-attestation-binds-exact-repository-workflow-artifact-and-digest",
    "phase-live-workflow-identity-validation-passes",
]
LIVE_COMMAND_BINDING_REQUIREMENTS = [
    "future-entrypoint-files-present",
    "live-cli-help-extraction-equals-command-grammars",
    "live-source-command-extraction-equals-command-grammars",
    "options-exits-and-mutation-boundaries-equal-command-grammars",
]
CORE_LIVE_COMMAND_BINDING_REQUIREMENTS = [
    "platform-native-entrypoint-file-present",
    "live-cli-help-extraction-equals-command-grammars",
    "live-source-command-extraction-equals-command-grammars",
    "options-exits-and-mutation-boundaries-equal-command-grammars",
    "windows-cargo-binary-identity-is-harness.exe",
]
EXPECTED_COMMAND_BINDING = {
    "schema": "repository-harness-command-implementation-binding/v1",
    "binding_state": "core-live-bridge-absent",
    "grammar_contract": "release/contracts/v1/command-grammars.json",
    "grammar_contract_sha256": "1afaf1eec75d10e7d474d5817144e1f3dc8add8b3ee9cdbb3f7610708cac6ef9",
    "grammar_schema": "release/contracts/v1/schemas/command-grammar-v1.schema.json",
    "grammar_schema_sha256": "99ef2353ec1dfd884f2583be91175a35577109808af804d47350e159198c42ee",
    "surfaces": {
        "core": {
            "phase": 2,
            "entrypoints": ["scripts/bin/harness", "scripts/bin/harness.exe"],
            "entrypoint_state": "live-platform-native",
            "live_binding": {
                "native_cli": "scripts/bin/harness",
                "windows_cli": "scripts/bin/harness.exe",
                "cargo_package": "harness-core",
                "cargo_binary": "harness",
                "source_command_definitions": "crates/harness-core/src/command_spec.rs",
                "help_argument": "--help",
                "requirements": CORE_LIVE_COMMAND_BINDING_REQUIREMENTS,
            },
        },
        "bridge": {
            "future_phase": 4,
            "future_entrypoints": ["scripts/bin/harness-v0-migrate", "scripts/bin/harness-v0-migrate.exe"],
            "entrypoint_state": "absent",
            "live_binding_gate": {"phase_acceptance": "required-before-phase-4-acceptance", "replacement_state": "live-cli-and-source-extraction-parity", "requirements": LIVE_COMMAND_BINDING_REQUIREMENTS},
        },
    },
}
EXPECTED_BOOTSTRAP = {
    "schema": "repository-harness-bootstrap-identity/v1",
    "repository": "hoangnb24/repository-harness",
    "production_v1_pipe_to_shell": "prohibited",
    "verification_order": ["download-immutable-bootstrap", "verify-pinned-github-artifact-attestation", "verify-exact-repository-workflow-artifact-and-digest", "execute-verified-file", "verify-ed25519-threshold-payload-index"],
    "core": {
        "tag_namespace": "harness-v1-core-v*",
        "protected_workflow": ".github/workflows/harness-v1-release.yml@refs/heads/main",
        "workflow_lifecycle": {
            "state": "source-present-unpromoted",
            "reserved_for_phase": 2,
            "source_path": ".github/workflows/harness-v1-release.yml",
            "production_bootstrap_acceptance": "blocked-until-promotion-gate",
            "promotion_gate": {"mode": "all-required", "requirements": PROMOTION_GATE_REQUIREMENTS},
            "external_evidence": {"repository_protection": "required-not-present", "pinned_artifact_attestation": "required-not-present"},
        },
        "roles": {"root": "core-root", "root_rotation": "core-root-rotation", "release": "core-release"},
        "sequence_namespaces": {"root": "core-root", "release": "core-release"},
        "signature_domains": {"trust_bundle": "repository-harness-core-trust-bundle-v1", "payload_index": "repository-harness-payload-index-v1", "rollback_authorization": "repository-harness-core-rollback-authorization-v1"},
    },
    "bridge": {
        "tag_namespace": "harness-v0-bridge-v*",
        "protected_workflow": ".github/workflows/harness-v0-bridge-release.yml@refs/heads/main",
        "workflow_lifecycle": {
            "state": "reserved-absent",
            "reserved_for_phase": 4,
            "source_path": None,
            "production_bootstrap_acceptance": "blocked-until-promotion-gate",
            "promotion_gate": {"mode": "all-required", "requirements": PROMOTION_GATE_REQUIREMENTS},
            "external_evidence": {"repository_protection": "not-applicable-until-live-source", "pinned_artifact_attestation": "not-applicable-until-live-source"},
        },
        "roles": {"root": "bridge-root", "root_rotation": "bridge-root-rotation", "release": "bridge-release"},
        "sequence_namespaces": {"root": "bridge-root", "release": "bridge-release"},
        "signature_domains": {"trust_bundle": "repository-harness-bridge-trust-bundle-v1", "payload_index": "repository-harness-bridge-payload-index-v1", "rollback_authorization": "repository-harness-bridge-rollback-authorization-v1", "availability_receipt": "repository-harness-bridge-availability-receipt-v1"},
    },
    "github_sigstore_role": "bootstrap-and-supplemental-not-payload-trust-root",
    "adjacent_downloaded_key_is_trust_anchor": False,
}


class ContractError(RuntimeError):
    pass


PASS_COUNT = 0


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def proof(label: str, function: Callable[[], None]) -> None:
    global PASS_COUNT
    function()
    PASS_COUNT += 1
    print(f"ok {PASS_COUNT:02d} - {label}")


def duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=duplicate_rejecting_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractError(f"invalid JSON {path.relative_to(ROOT)}: {error}") from error


def expect_failure(function: Callable[[], Any], label: str) -> None:
    try:
        function()
    except (ContractError, OSError, sqlite3.Error, ValueError, binascii.Error):
        return
    raise ContractError(f"negative fixture unexpectedly passed: {label}")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def jcs_string(value: str) -> str:
    check(not any(0xD800 <= ord(ch) <= 0xDFFF for ch in value), "JCS rejects lone surrogate")
    short = {8: "\\b", 9: "\\t", 10: "\\n", 12: "\\f", 13: "\\r"}
    output = ['"']
    for character in value:
        codepoint = ord(character)
        if character == '"':
            output.append('\\"')
        elif character == "\\":
            output.append("\\\\")
        elif codepoint in short:
            output.append(short[codepoint])
        elif codepoint < 0x20:
            output.append(f"\\u{codepoint:04x}")
        else:
            output.append(character)
    output.append('"')
    return "".join(output)


def jcs(value: Any) -> bytes:
    def render(item: Any) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, int) and not isinstance(item, bool):
            check(abs(item) <= 9007199254740991, "JCS integer outside interoperable range")
            return str(item)
        if isinstance(item, float):
            raise ContractError("signed contract documents forbid floating-point numbers")
        if isinstance(item, str):
            return jcs_string(item)
        if isinstance(item, list):
            return "[" + ",".join(render(entry) for entry in item) + "]"
        if isinstance(item, dict):
            keys = sorted(item, key=lambda key: key.encode("utf-16-be", "surrogatepass"))
            return "{" + ",".join(jcs_string(key) + ":" + render(item[key]) for key in keys) + "}"
        raise ContractError(f"unsupported JCS value: {type(item).__name__}")

    return render(value).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return sha256_bytes(jcs(value))


def signed_message(domain: str, value: Any) -> bytes:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + jcs(value)).digest()


def crypto_helper(arguments: list[str]) -> bool:
    helper_value = os.environ.get("V1_CONTRACT_CRYPTO")
    check(helper_value is not None, "strict Ed25519 helper path is not configured")
    helper = Path(helper_value)
    check(helper.is_file(), f"strict Ed25519 helper is missing: {helper}")
    result = subprocess.run(
        [str(helper), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    check(result.returncode in (0, 1), f"strict Ed25519 helper failed with exit {result.returncode}")
    return result.returncode == 0


def ed25519_public_key_valid(public_key: bytes) -> bool:
    return len(public_key) == 32 and crypto_helper(["public-key", public_key.hex()])


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    return (len(public_key) == 32 and len(signature) == 64
            and crypto_helper(["verify", public_key.hex(), message.hex(), signature.hex()]))


def json_type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def validate_schema(value: Any, schema: dict[str, Any], path: str = "$",
                    root_schema: dict[str, Any] | None = None) -> None:
    root_schema = root_schema or schema
    if "$ref" in schema:
        reference = schema["$ref"]
        check(reference.startswith("#/$defs/"), f"{path}: unsupported schema reference {reference}")
        definition = reference.removeprefix("#/$defs/")
        check(definition in root_schema.get("$defs", {}), f"{path}: missing schema definition {definition}")
        validate_schema(value, root_schema["$defs"][definition], path, root_schema)
        return
    if "const" in schema:
        check(value == schema["const"], f"{path}: expected const {schema['const']!r}")
    if "enum" in schema:
        check(value in schema["enum"], f"{path}: value outside enum")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        check(any(json_type_matches(value, expected) for expected in types), f"{path}: wrong type")
    if isinstance(value, dict):
        required = schema.get("required", [])
        for field in required:
            check(field in value, f"{path}: missing required field {field}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            check(not extra, f"{path}: unknown fields {extra}")
        for field, child in value.items():
            if field in properties:
                validate_schema(child, properties[field], f"{path}.{field}", root_schema)
    if isinstance(value, list):
        if "minItems" in schema:
            check(len(value) >= schema["minItems"], f"{path}: too few items")
        if "maxItems" in schema:
            check(len(value) <= schema["maxItems"], f"{path}: too many items")
        if "items" in schema:
            for index, child in enumerate(value):
                validate_schema(child, schema["items"], f"{path}[{index}]", root_schema)
        if schema.get("uniqueItems") is True:
            identities = [jcs(child) for child in value]
            check(len(identities) == len(set(identities)), f"{path}: duplicate array item")
    if isinstance(value, str) and "pattern" in schema:
        check(re.search(schema["pattern"], value) is not None, f"{path}: pattern mismatch")
    if isinstance(value, str) and "minLength" in schema:
        check(len(value) >= schema["minLength"], f"{path}: string too short")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema:
            check(value >= schema["minimum"], f"{path}: below minimum")
        if "maximum" in schema:
            check(value <= schema["maximum"], f"{path}: above maximum")


def safe_path(value: str, *, allow_harness: bool = False) -> str:
    check(isinstance(value, str) and value, "path must be a nonempty string")
    check(unicodedata.is_normalized("NFC", value), f"path is not NFC: {value!r}")
    check(not value.startswith(("/", "//")), f"absolute/UNC path: {value}")
    check(re.match(r"^[A-Za-z]:", value) is None, f"drive path: {value}")
    check("\\" not in value and "\0" not in value, f"backslash/NUL path: {value}")
    check(not any(ord(character) < 0x20 for character in value), f"control path: {value}")
    parts = value.split("/")
    check(all(part not in ("", ".", "..") for part in parts), f"unsafe path component: {value}")
    for part in parts:
        check(":" not in part, f"Windows ADS separator in path component: {value}")
        check(part == part.rstrip(" ."), f"trailing dot/space component: {value}")
        basename = part.split(".", 1)[0].upper()
        check(basename not in WINDOWS_DEVICES, f"Windows device component: {value}")
    check(".git" not in [part.casefold() for part in parts], f"Git internal path: {value}")
    if parts[0].casefold() == ".harness":
        allowed = value == ".harness/manifest.json" or value.startswith(".harness/recovery/") or value.startswith(".harness/legacy/v0-conversion/")
        check(allow_harness and allowed, f"undeclared .harness path: {value}")
    return unicodedata.normalize("NFC", value).casefold()


def recursively_reject_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            check(normalized not in FORBIDDEN_FIELDS, f"{path}: forbidden field {key}")
            recursively_reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            recursively_reject_forbidden_fields(child, f"{path}[{index}]")


def key_map(key_objects: list[dict[str, Any]]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for entry in key_objects:
        check(set(entry) == {"key_id", "algorithm", "public_key_base64", "test_fixture"}, "test key fields are closed")
        check(entry["algorithm"] == "ed25519", "key algorithm must be Ed25519")
        check(entry["test_fixture"] is True, "fixture key marker missing")
        raw = base64.b64decode(entry["public_key_base64"], validate=True)
        check(ed25519_public_key_valid(raw), "test public key is not canonical prime-order Ed25519")
        expected = "ed25519-sha256:" + sha256_bytes(raw)
        check(entry["key_id"] == expected, "key ID does not bind raw public key")
        check(entry["key_id"] not in result, "duplicate key ID")
        result[entry["key_id"]] = raw
    return result


def validate_trust_bundle(bundle: dict[str, Any], expected_domain: str, expected_role: str) -> tuple[dict[str, bytes], dict[str, bytes], set[str]]:
    validate_schema(bundle, load_json(SCHEMAS / "trust-bundle-v1.schema.json"))
    check(bundle["trust_domain"] == expected_domain, "trust bundle domain mismatch")
    check(bundle.get("test_fixture_notice") == "UNSAFE-TEST-ONLY-NOT-FOR-RELEASE", "test trust bundle warning missing")
    check(bundle["roots"]["threshold"] == 2 and len(bundle["roots"]["keys"]) == 3, "root bundle must be 2-of-3")
    roots = key_map(bundle["roots"]["keys"])
    check(len(bundle["roles"]) == 1, "fixture bundle has one release role")
    role = bundle["roles"][0]
    check(set(role) == {"name", "threshold", "keys"}, "release role fields are closed")
    check(role["name"] == expected_role and role["threshold"] == 2 and len(role["keys"]) == 3, "release role must be named 2-of-3")
    release = key_map(role["keys"])
    check(not set(roots) & set(release), "root and release role keys must differ")
    encoded = json.dumps(bundle).lower()
    check("private" not in encoded and "seed" not in encoded, "trust bundle contains private fixture material")
    return roots, release, set(bundle["revoked_key_ids"])


def verify_envelope(payload: Any, envelope_value: dict[str, Any], domain_tag: str,
                    keys: dict[str, bytes], threshold: int, expected_domain: str,
                    expected_role: str, expected_sequence: int,
                    revoked: set[str] | None = None) -> set[str]:
    validate_schema(envelope_value, load_json(SCHEMAS / "signature-envelope-v1.schema.json"))
    check(envelope_value["trust_domain"] == expected_domain, "envelope trust domain mismatch")
    check(envelope_value["role"] == expected_role, "envelope role mismatch")
    check(envelope_value["sequence"] == expected_sequence, "envelope sequence mismatch")
    check(envelope_value["payload_sha256"] == canonical_digest(payload), "detached envelope digest mismatch")
    message = signed_message(domain_tag, payload)
    valid: set[str] = set()
    revoked = revoked or set()
    for signature in envelope_value["signatures"]:
        key_id = signature["key_id"]
        if key_id not in keys or key_id in revoked or key_id in valid:
            continue
        try:
            raw_signature = base64.b64decode(signature["signature"], validate=True)
        except binascii.Error:
            continue
        if ed25519_verify(keys[key_id], message, raw_signature):
            valid.add(key_id)
    check(len(valid) >= threshold, f"signature threshold not met: {len(valid)}/{threshold}")
    return valid


def validate_payload_index(index: dict[str, Any], domain: str, role: str) -> None:
    validate_schema(index, load_json(SCHEMAS / "payload-index-v1.schema.json"))
    check(index["trust_domain"] == domain and index["role"] == role, "payload index role/domain mismatch")
    if domain.endswith("core"):
        check(index["schema"] == "repository-harness-payload-index/v1", "core index schema")
        check(index["tag"].startswith("harness-v1-core-v"), "core tag namespace")
    else:
        check(index["schema"] == "repository-harness-bridge-payload-index/v1", "bridge index schema")
        check(index["tag"].startswith("harness-v0-bridge-v"), "bridge tag namespace")
    ids: set[str] = set()
    collisions: set[str] = set()
    for asset in index["assets"]:
        check(asset["id"] not in ids, "duplicate payload asset ID")
        ids.add(asset["id"])
        source_collision = safe_path(asset["source"])
        destination_collision = safe_path(asset["destination"])
        check(destination_collision not in collisions, "payload destination collision")
        collisions.add(destination_collision)
        source = ROOT / PurePosixPath(asset["source"])
        check(source.is_file(), f"indexed source missing: {asset['source']}")
        check(source_collision, "source collision key is empty")
        check(source.stat().st_size == asset["bytes"] and sha256_file(source) == asset["sha256"], "indexed source identity mismatch")


def validate_manifest(value: dict[str, Any]) -> None:
    validate_schema(value, load_json(SCHEMAS / "manifest-v1.schema.json"))
    recursively_reject_forbidden_fields(value)
    semver = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
    parsed_versions: dict[str, tuple[int, int, int]] = {}
    for field, version in value["compatibility"].items():
        match = semver.fullmatch(version)
        check(match is not None, f"invalid semantic version in compatibility.{field}")
        parsed_versions[field] = tuple(int(part) for part in match.groups())
    check(parsed_versions["cli_min"] <= parsed_versions["cli_max"], "CLI compatibility range is reversed")
    check(parsed_versions["template_release_min"] <= parsed_versions["template_release_max"], "template compatibility range is reversed")
    role_ids: set[str] = set()
    marker_ids: set[str] = set()
    collisions: set[str] = set()
    for role in value["roles"]:
        check(role["role"] not in role_ids, "duplicate manifest role")
        role_ids.add(role["role"])
        collision = safe_path(role["path"], allow_harness=True)
        check(collision not in collisions, "manifest path collision")
        collisions.add(collision)
        if role["required"]:
            check(role["activation"] != "disabled", "required role cannot be disabled")
        if role["ownership"] == "target-owned":
            check(role["update_policy"] == "never-auto-patch", "target-owned role must never auto patch")
        if role["ownership"] == "managed-block":
            check("marker" in role and role["marker"] not in marker_ids, "managed block marker missing/duplicate")
            marker_ids.add(role["marker"])
        if role["activation"] == "unresolved":
            check(role["unresolved_markers"], "unresolved role must name markers")
            pattern = re.compile(rf"^REPOSITORY-HARNESS-UNRESOLVED\({re.escape(role['role'])}:[a-z0-9][a-z0-9-]*\)$")
            check(all(pattern.fullmatch(marker) for marker in role["unresolved_markers"]), "unresolved marker identity/path contract")
        else:
            check(not role["unresolved_markers"], "non-unresolved role cannot list unresolved markers")
    if value["repository_mode"] == "converted-v1-with-archive":
        check("conversion_receipt" in value, "converted mode requires embedded receipt")
        receipt = value["conversion_receipt"]
        expected_prefix = f".harness/legacy/v0-conversion/{receipt['conversion_id']}/"
        safe_path(receipt["archive_path"], allow_harness=True)
        check(receipt["archive_path"].startswith(expected_prefix), "conversion receipt archive placement mismatch")
        if receipt["confidentiality_mode"] == "encrypted-age-x25519":
            check(receipt["recipient_fingerprints"] and "plaintext_risk_acknowledged" not in receipt, "encrypted receipt recipient/mode mismatch")
        else:
            check(not receipt["recipient_fingerprints"] and receipt.get("plaintext_risk_acknowledged") is True, "plaintext receipt must record explicit risk acknowledgement")
    else:
        check("conversion_receipt" not in value, "non-converted mode cannot claim receipt")


def validate_archive_manifest(value: dict[str, Any]) -> None:
    validate_schema(value, load_json(SCHEMAS / "archive-manifest-v1.schema.json"))
    collisions: set[str] = set()
    for member in value["members"]:
        collision = safe_path(member["path"])
        check(collision not in collisions, "archive member path collision")
        collisions.add(collision)
    if value["confidentiality_mode"] == "encrypted-age-x25519":
        check(value["recipient_fingerprints"], "encrypted archive recipient missing")
        check("plaintext_risk_acknowledged" not in value, "encrypted archive cannot claim plaintext override")
    else:
        check(not value["recipient_fingerprints"], "plaintext archive cannot claim encryption recipient")
        check(value.get("plaintext_risk_acknowledged") is True, "plaintext archive risk acknowledgement missing")


def validate_command_grammar(value: dict[str, Any]) -> None:
    validate_schema(value, load_json(SCHEMAS / "command-grammar-v1.schema.json"))
    core = value["core"]
    bridge = value["bridge"]
    check(core["binary"] == ["scripts/bin/harness", "scripts/bin/harness.exe"], "core binary names changed")
    check(core["top_level"] == [entry["name"] for entry in EXPECTED_CORE_COMMANDS], "core top-level command array changed")
    check(core["commands"] == EXPECTED_CORE_COMMANDS, "core command definitions changed")
    check(core["version_alias"] == "--version", "core version alias changed")
    check(core["forbidden_top_level"] == ["migrate", "inspect", "export", "preview", "apply", "resume", "rollback", "init", "intake", "story", "query", "db"], "core forbidden command array changed")
    check(bridge["binary"] == ["scripts/bin/harness-v0-migrate", "scripts/bin/harness-v0-migrate.exe"], "bridge binary names changed")
    check(bridge["top_level"] == [entry["name"] for entry in EXPECTED_BRIDGE_COMMANDS], "bridge top-level command array changed")
    check(bridge["commands"] == EXPECTED_BRIDGE_COMMANDS, "bridge command definitions changed")
    check(bridge["forbidden_top_level"] == ["install", "update", "audit", "scaffold", "status", "migrate", "init", "query"], "bridge forbidden command array changed")
    check(value["deterministic_non_interactive"] == {"confirmation_requires": ["--non-interactive", "--accept-preview-sha256"], "preview_digest_algorithm": "sha256-rfc8785", "input_drift_exit": 4}, "deterministic non-interactive contract changed")


def validate_command_binding(value: dict[str, Any], repository_root: Path = ROOT) -> None:
    validate_schema(value, load_json(SCHEMAS / "command-implementation-binding-v1.schema.json"))
    check(value == EXPECTED_COMMAND_BINDING, "command implementation core-live/bridge-absent binding changed")
    grammar_path = ROOT / value["grammar_contract"]
    grammar_schema_path = ROOT / value["grammar_schema"]
    check(sha256_file(grammar_path) == value["grammar_contract_sha256"], "command grammar binding digest mismatch")
    check(sha256_file(grammar_schema_path) == value["grammar_schema_sha256"], "command grammar schema binding digest mismatch")
    grammar = load_json(grammar_path)
    core = value["surfaces"]["core"]
    bridge = value["surfaces"]["bridge"]
    check(core["entrypoints"] == grammar["core"]["binary"], "core live entrypoints differ from grammar binary identities")
    check(bridge["future_entrypoints"] == grammar["bridge"]["binary"], "bridge future entrypoints differ from grammar binary identities")
    for relative in core["entrypoints"] + bridge["future_entrypoints"]:
        safe_path(relative)
    native_relative = core["live_binding"]["windows_cli" if os.name == "nt" else "native_cli"]
    native_entrypoint = repository_root / native_relative
    check(native_entrypoint.is_file(), f"platform-native core entrypoint is missing: {native_relative}")
    if os.name != "nt":
        check(os.access(native_entrypoint, os.X_OK), f"platform-native core entrypoint is not executable: {native_relative}")
    result = subprocess.run(
        [str(native_entrypoint), core["live_binding"]["help_argument"]],
        cwd=repository_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    check(result.returncode == 0 and result.stderr == "", "live core help extraction failed")
    try:
        live_help = json.loads(result.stdout, object_pairs_hook=duplicate_rejecting_object)
    except json.JSONDecodeError as error:
        raise ContractError(f"live core help is not machine JSON: {error}") from error
    check(live_help == grammar["core"], "live core help differs from frozen grammar")

    source_path = repository_root / core["live_binding"]["source_command_definitions"]
    source = source_path.read_text(encoding="utf-8")
    match = re.search(
        r"// CORE_COMMAND_SPEC_JSON_BEGIN.*?pub const CORE_COMMAND_SPEC_JSON: &str = r#\"(?P<json>.*?)\"#;.*?// CORE_COMMAND_SPEC_JSON_END",
        source,
        re.DOTALL,
    )
    check(match is not None, "live source command definition markers are missing")
    try:
        source_commands = json.loads(match.group("json"), object_pairs_hook=duplicate_rejecting_object)
    except json.JSONDecodeError as error:
        raise ContractError(f"live source command definitions are invalid JSON: {error}") from error
    check(source_commands == grammar["core"], "live source command definitions differ from frozen grammar")
    cargo = (repository_root / "crates" / "harness-core" / "Cargo.toml").read_text(encoding="utf-8")
    check('name = "harness-core"' in cargo and 'name = "harness"' in cargo, "Cargo core/Windows binary identity differs")
    for relative in bridge["future_entrypoints"]:
        check(not os.path.lexists(repository_root / relative), f"Phase 4 bridge entrypoint appeared before its live gate: {relative}")


def validate_bootstrap(value: dict[str, Any], repository_root: Path = ROOT) -> None:
    validate_schema(value, load_json(SCHEMAS / "bootstrap-identity-v1.schema.json"))
    check(value == EXPECTED_BOOTSTRAP, "bootstrap identity/order/domain/role/namespace contract changed")
    core_ids = set(value["core"]["roles"].values()) | set(value["core"]["sequence_namespaces"].values())
    bridge_ids = set(value["bridge"]["roles"].values()) | set(value["bridge"]["sequence_namespaces"].values())
    check(core_ids.isdisjoint(bridge_ids), "bootstrap core/bridge role or sequence namespace crossover")
    check(set(value["core"]["signature_domains"].values()).isdisjoint(value["bridge"]["signature_domains"].values()), "bootstrap signature domain crossover")
    for surface in ("core", "bridge"):
        workflow_reference = value[surface]["protected_workflow"]
        workflow_path, separator, branch = workflow_reference.partition("@")
        check(separator == "@" and branch == "refs/heads/main", f"{surface} reserved workflow reference is not exact")
        safe_path(workflow_path)
        lifecycle = value[surface]["workflow_lifecycle"]
        check(lifecycle["production_bootstrap_acceptance"] == "blocked-until-promotion-gate", f"{surface} production bootstrap is not blocked")
        if surface == "core":
            check(lifecycle["state"] == "source-present-unpromoted" and lifecycle["source_path"] == workflow_path, "core workflow lifecycle/source path mismatch")
            check(lifecycle["external_evidence"] == {"repository_protection": "required-not-present", "pinned_artifact_attestation": "required-not-present"}, "core external promotion evidence was claimed early")
            workflow = repository_root / workflow_path
            check(workflow.is_file(), "core workflow source is missing")
            text = workflow.read_text(encoding="utf-8")
            for fragment in [
                "Repository Harness V1 Proof (Unpromoted)",
                "github.repository == 'hoangnb24/repository-harness'",
                "prove-before-promotion:",
                "promotion-blocked:",
                "needs: prove-before-promotion",
                "repository-protection and pinned artifact-attestation evidence are not present",
                "exit 1",
            ]:
                check(fragment in text, f"core workflow source omits promotion guard: {fragment}")
            check("contents: read" in text and "contents: write" not in text and "id-token: write" not in text, "unpromoted core workflow has production write permission")
            for forbidden in ["gh release create", "git tag", "git push", "attest-build-provenance"]:
                check(forbidden not in text, f"unpromoted core workflow contains production action: {forbidden}")
        else:
            check(lifecycle["state"] == "reserved-absent" and lifecycle["source_path"] is None, "bridge workflow lifecycle is not reserved-absent")
            check(not os.path.lexists(repository_root / workflow_path), f"bridge reserved workflow appeared before its promotion gate: {workflow_path}")


def validate_release_inventory(value: dict[str, Any], *, live_sources: bool = False) -> None:
    validate_schema(value, load_json(SCHEMAS / "release-artifacts-v1.schema.json"))
    check(value["platforms"] == EXPECTED_RELEASE_PLATFORMS, "release platform/binary array changed")
    check(len({entry["platform"] for entry in value["platforms"]}) == 5, "release platform names are not unique")
    check(len({entry["binary"] for entry in value["platforms"]}) == 5, "release binary names are not unique")
    check(all(entry["checksum"] == f"{entry['binary']}.sha256" for entry in value["platforms"]), "release checksum name drift")
    if not live_sources:
        return

    workflow = (ROOT / value["workflow"]).read_text(encoding="utf-8")
    matches = re.findall(
        r"^\s*- platform: (\S+)\n\s+target: (\S+)\n\s+runner: (\S+)\n\s+binary: (\S+)\s*$",
        workflow,
        re.MULTILINE,
    )
    live = [
        {"platform": platform, "target": target, "runner": runner, "binary": binary, "checksum": f"{binary}.sha256"}
        for platform, target, runner, binary in matches
    ]
    check(live == value["platforms"], "release workflow matrix differs from frozen inventory")
    upload_match = re.search(r"\n\s+path: \|\n(?P<paths>(?:\s+dist/[^\n]+\n)+)\s+if-no-files-found: error", workflow)
    check(upload_match is not None, "release workflow upload path block missing")
    upload_paths = [line.strip() for line in upload_match.group("paths").splitlines()]
    check(upload_paths == ["dist/${{ matrix.binary }}", "dist/${{ matrix.binary }}.sha256"], "release workflow uploads an unindexed artifact class")

    build = (ROOT / value["build_script"]).read_text(encoding="utf-8")
    mappings = re.findall(r'^\s*([^ )]+)\) platform="([^"]+)" ;;$', build, re.MULTILINE)
    expected_mappings = [(entry["target"], entry["platform"]) for entry in value["platforms"]]
    check(mappings == expected_mappings, "release build target/platform mapping differs from frozen inventory")
    for fragment in ['binary_name="harness-cli"', 'artifact_name="harness-cli-$platform"', 'artifact_name="$artifact_name.exe"', '"$(basename "$artifact").sha256"']:
        check(fragment in build, f"release build binary/checksum rule drift: {fragment}")


def parse_utc_timestamp(value: str) -> datetime:
    check(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value) is not None, "timestamp must be exact UTC Z form")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise ContractError(f"invalid UTC timestamp: {value}") from error
    check(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed), "timestamp must be timezone-aware UTC")
    return parsed


def validate_availability_receipt(value: dict[str, Any], policy: dict[str, Any]) -> None:
    validate_schema(value, load_json(SCHEMAS / "availability-receipt-v1.schema.json"))
    try:
        year, month = (int(part) for part in value["month"].split("-"))
        calendar.monthrange(year, month)
    except (ValueError, TypeError) as error:
        raise ContractError("availability receipt month is invalid") from error
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    next_month = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)
    checks = [parse_utc_timestamp(timestamp) for timestamp in value["weekly_checks"]]
    check(all(month_start <= observed < next_month for observed in checks), "availability timestamp outside declared month")
    for earlier, later in zip(checks, checks[1:]):
        seconds = (later - earlier).total_seconds()
        check(0 < seconds <= 7 * 86400, "availability timestamps decrease, repeat, or exceed seven exact days")
    check(0 <= (checks[0] - month_start).total_seconds() <= 7 * 86400, "availability checks do not cover month start")
    check(0 < (next_month - checks[-1]).total_seconds() <= 7 * 86400, "availability checks do not cover month end")

    bridge_policy = policy["bridge_assets"]
    required_categories = set(bridge_policy["complete_set"])
    supported_platforms = set(bridge_policy["supported_platforms"])
    platform_scoped = set(bridge_policy["platform_scoped_categories"])
    identities: set[tuple[str, str]] = set()
    for asset in value["assets"]:
        safe_path(asset["path"])
        identity = (asset["category"], asset["platform"])
        check(identity not in identities, f"duplicate availability asset identity: {identity}")
        identities.add(identity)
        if asset["category"] in platform_scoped:
            check(asset["platform"] in supported_platforms, "platform-scoped availability asset lacks a supported platform")
        else:
            check(asset["platform"] == "all", "global availability asset must use platform=all")
    check({category for category, _ in identities} == required_categories, "availability receipt does not bind the policy complete_set")
    for category in platform_scoped:
        represented = {platform for candidate, platform in identities if candidate == category}
        check(represented == supported_platforms, f"availability category lacks a supported platform: {category}")


def parse_changeset_fixture(path: Path, matrix: dict[str, Any]) -> None:
    operations: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, object_pairs_hook=duplicate_rejecting_object)
        except json.JSONDecodeError as error:
            raise ContractError(f"{path.name}:{line_number}: malformed JSON") from error
        check(isinstance(value, dict), f"{path.name}:{line_number}: operation is not an object")
        operations.append(value)
    check(operations, f"{path.name}: empty changeset")
    header = operations[0]
    check(header.get("op") == "changeset.header" and header.get("version") == 1, f"{path.name}: header version/op")
    check(isinstance(header.get("run_id"), str) and header["run_id"].strip(), f"{path.name}: blank run_id")
    check(isinstance(header.get("base_schema_version"), int) and 1 <= header["base_schema_version"] <= 13, f"{path.name}: base schema range")
    accepted = {entry["op"]: set(entry["versions"]) for entry in matrix["operations"]}
    for operation in operations[1:]:
        op = operation.get("op")
        version = operation.get("version", matrix["missing_operation_version_defaults_to"])
        check(op in accepted, f"{path.name}: unknown operation {op}")
        check(version in accepted[op], f"{path.name}: unsupported operation version {version}")


def proof_schemas_and_examples() -> None:
    schema_files = sorted(SCHEMAS.glob("*.schema.json"))
    check(len(schema_files) == 12, "expected twelve versioned JSON schemas")
    for path in schema_files:
        schema = load_json(path)
        check(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"schema dialect missing: {path.name}")
        check(schema.get("type") == "object" and schema.get("additionalProperties") is False, f"root schema is not closed: {path.name}")
    for path in sorted(FIXTURES.rglob("*.signatures.json")):
        envelope_value = load_json(path)
        check(path.read_bytes() == jcs(envelope_value), f"detached signature envelope is not canonical JSON: {path.relative_to(ROOT)}")

    for name in ["manifest.json", "unresolved-manifest.json", "converted-manifest.json"]:
        validate_manifest(load_json(POS / name))
    validate_schema(load_json(POS / "output-envelope.json"), load_json(SCHEMAS / "output-envelope-v1.schema.json"))
    validate_archive_manifest(load_json(POS / "archive" / "manifest.json"))
    validate_archive_manifest(load_json(POS / "plaintext-override-archive-manifest.json"))
    validate_schema(load_json(POS / "authorized-rollback.json"), load_json(SCHEMAS / "rollback-authorization-v1.schema.json"))
    validate_schema(load_json(POS / "availability-receipt.json"), load_json(SCHEMAS / "availability-receipt-v1.schema.json"))
    expect_failure(lambda: validate_manifest(load_json(NEG / "forbidden-field-manifest.json")), "manifest forbidden operational field")
    for name in ["required-disabled-manifest.json", "target-owned-auto-patch-manifest.json", "unsafe-path-manifest.json"]:
        expect_failure(lambda fixture=name: validate_manifest(load_json(NEG / fixture)), name)
    expect_failure(lambda: validate_manifest(load_json(NEG / "malformed-schema-manifest.json")), "manifest schema discriminator mismatch")
    expect_failure(lambda: validate_schema(load_json(NEG / "output-operation-unknown-field.json"), load_json(SCHEMAS / "output-envelope-v1.schema.json")), "nested output operation unknown field")
    expect_failure(lambda: validate_archive_manifest(load_json(NEG / "plaintext-without-ack-archive-manifest.json")), "plaintext archive without risk acknowledgement")


def proof_grammar() -> None:
    grammar = load_json(CONTRACT / "command-grammars.json")
    validate_command_grammar(grammar)
    binding = load_json(CONTRACT / "command-implementation-binding.json")
    validate_command_binding(binding)
    core = grammar["core"]
    bridge = grammar["bridge"]
    check(core["top_level"] == ["install", "update", "audit", "scaffold", "status", "version"], "core grammar is not exactly six commands")
    check(bridge["top_level"] == ["inspect", "export", "preview", "apply", "resume", "rollback", "version"], "bridge grammar is not exactly seven commands")
    check(not set(core["top_level"]) & {"migrate", "inspect", "export", "preview", "apply", "resume", "rollback"}, "bridge/migrate leaked into core")
    for command in core["commands"]:
        if command["name"] in {"audit", "status", "version"}:
            check(command["mutation"] == "none", f"read-only core boundary changed: {command['name']}")
        if command["name"] in {"install", "update", "scaffold"}:
            check("--preview" in command["options"] and "--resume" in command["options"] and "--rollback" in command["options"], "mutator preview/recovery options missing")
            check("--non-interactive" in command["options"] and "--accept-preview-sha256" in command["options"], "deterministic non-interactive binding missing")
    for command in bridge["commands"]:
        if command["name"] in {"inspect", "preview", "version"}:
            check(command["mutation"] == "none", f"read-only bridge boundary changed: {command['name']}")
    cases = load_json(FIXTURES / "grammar-cases.json")
    check(cases["core_valid"] == core["top_level"] + ["--version"], "core grammar positive snapshot")
    check(cases["bridge_valid"] == bridge["top_level"], "bridge grammar positive snapshot")
    check(set(cases["core_invalid"]).isdisjoint(core["top_level"]), "invalid core command accepted")
    check(set(cases["bridge_invalid"]).isdisjoint(bridge["top_level"]), "invalid bridge command accepted")
    expect_failure(lambda: validate_command_grammar(load_json(NEG / "extra-core-command.json")), "extra core command")
    expect_failure(lambda: validate_command_grammar(load_json(NEG / "reordered-core-command.json")), "reordered core command")
    for name in ["command-binding-entrypoint-mismatch.json", "command-binding-state-mismatch.json", "command-binding-unknown-field.json"]:
        expect_failure(lambda fixture=name: validate_command_binding(load_json(NEG / fixture)), name)
    with tempfile.TemporaryDirectory(prefix="harness-v1-bridge-entrypoint-") as temporary:
        temporary_root = Path(temporary)
        entrypoint = temporary_root / binding["surfaces"]["bridge"]["future_entrypoints"][0]
        entrypoint.parent.mkdir(parents=True)
        entrypoint.write_bytes(b"UNSAFE TEST ONLY future bridge entrypoint")
        expect_failure(lambda root=temporary_root: validate_command_binding(binding, root), "bridge entrypoint appeared before live binding gate")
    audit = load_json(CONTRACT / "audit-rules.json")
    check(audit["process_execution_count"] == 0 and audit["forbidden_process_classes"], "audit zero-process rule missing")
    check("identity-stable-preview-to-commit" in audit["safe_path_rules"] and "pinned-root-fd-component-relative-no-follow" in audit["safe_path_rules"], "descriptor-anchored path-swap rule missing")
    check("no-backslash-colon-nul-control-or-trailing-dot-space" in audit["safe_path_rules"], "Windows ADS rejection rule missing")
    check("pre-copy-post-identity-size-hash-equal" in audit["safe_path_rules"], "capture integrity rule missing")
    check(audit["digest"] == "sha256-exact-bytes-no-reencoding-or-line-ending-normalization", "exact-byte digest rule changed")


def noncomment_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def proof_path_inventory() -> None:
    ledger = load_json(CONTRACT / "path-dispositions.json")
    allowed = set(ledger["allowed_dispositions"])
    entries = ledger["entries"]
    identities: set[tuple[str, str]] = set()
    by_surface: dict[str, set[str]] = {}
    by_path: dict[str, str] = {}
    for entry in entries:
        check(set(entry) == {"path", "surface", "disposition", "reason"}, "ledger entry fields are closed")
        identity = (entry["surface"], entry["path"])
        check(identity not in identities, f"duplicate ledger disposition: {identity}")
        identities.add(identity)
        check(entry["disposition"] in allowed and entry["reason"].strip(), f"invalid disposition: {identity}")
        by_surface.setdefault(entry["surface"], set()).add(entry["path"])
        if entry["path"] in by_path:
            check(by_path[entry["path"]] == entry["disposition"], f"path has conflicting dispositions: {entry['path']}")
        by_path[entry["path"]] = entry["disposition"]

    installer = set(noncomment_lines(ROOT / "scripts" / "harness-install-files.txt"))
    check(by_surface.get("installer-manifest") == installer, "installer manifest is not covered one-to-one")
    for path in installer:
        check((ROOT / path).is_file(), f"current installer source missing: {path}")
    schema_paths = {path.relative_to(ROOT).as_posix() for path in (ROOT / "scripts" / "schema").glob("*.sql")}
    check(by_surface.get("schema-discovery") == schema_paths, "discovered schema payload is not covered one-to-one")
    generated = {
        "CLAUDE.md",
        "scripts/bin/harness-cli",
        "scripts/bin/harness-cli.exe",
        "scripts/bin/harness",
        "scripts/bin/harness.exe",
    }
    check(by_surface.get("installed-generated") == generated, "generated install destinations changed")
    release_inventory = load_json(CONTRACT / "release-artifacts.json")
    validate_release_inventory(release_inventory, live_sources=True)
    releases = {f"dist/{entry[field]}" for entry in release_inventory["platforms"] for field in ("binary", "checksum")}
    check(by_surface.get("release-artifact") == releases, "five-platform release paths changed")
    expect_failure(lambda: validate_release_inventory(load_json(NEG / "release-extra-platform.json")), "extra release platform")
    expect_failure(lambda: validate_release_inventory(load_json(NEG / "release-binary-drift.json")), "release binary drift")
    for surface in ("bootstrap-source", "release-source"):
        for path in by_surface.get(surface, set()):
            check((ROOT / path).is_file(), f"inventoried release source missing: {path}")
    phase1_contract_files = {path.relative_to(ROOT).as_posix() for path in CONTRACT.rglob("*") if path.is_file()}
    check(by_surface.get("phase1-release-contract") == phase1_contract_files, "Phase 1 release contract sources are not covered one-to-one")
    for path in phase1_contract_files:
        expected_disposition = "bridge-only-legacy" if path.startswith("release/contracts/v1/v0") else "source-only"
        check(by_path[path] == expected_disposition, f"Phase 1 release contract disposition differs: {path}")

    core_index = load_json(POS / "core-payload-index.json")
    indexed = {asset["source"] for asset in core_index["assets"]}
    for asset in core_index["assets"]:
        check(by_path.get(asset["source"]) == asset["disposition"] and asset["disposition"] in {"managed-v1", "optional-v1"}, "core index/ledger disposition mismatch")
    bridge_index = load_json(POS / "bridge-payload-index.json")
    for asset in bridge_index["assets"]:
        check(by_path.get(asset["source"]) == "bridge-only-legacy" and asset["disposition"] == "bridge-only-legacy", "bridge index/ledger disposition mismatch")
    candidate = set(noncomment_lines(NEG / "unindexed-core-paths.txt"))
    expect_failure(lambda: check(candidate <= indexed, "unindexed core payload path"), "unindexed path")

    def forbidden(path: str) -> bool:
        return (path in {"harness.db", "harness.db-wal", "harness.db-shm", "scripts/bin/harness-cli", "scripts/bin/harness-cli.exe"}
                or path.startswith("scripts/schema/") or path.startswith(".harness/changesets/")
                or by_path.get(path) == "forbidden-v0-operational")

    forbidden_candidate = noncomment_lines(NEG / "forbidden-core-paths.txt")
    check(any(not forbidden(path) for path in forbidden_candidate), "negative fixture needs an allowed control")
    check(all(forbidden(path) for path in forbidden_candidate[1:]), "forbidden core path class escaped")
    expect_failure(lambda: check(not any(forbidden(path) for path in forbidden_candidate), "forbidden V0 path entered core"), "forbidden V0 core payload")


def extract_parser_operations() -> set[str]:
    source = (ROOT / "crates" / "harness-cli" / "src" / "infrastructure.rs").read_text(encoding="utf-8")
    start = source.index("fn apply_changeset_operation(")
    end = source.index("\nfn ensure_story_exists", start)
    body = source[start:end]
    return set(re.findall(r'^\s*"([a-z0-9_.-]+)"(?:\s+if[^=]*)?\s*=>', body, re.MULTILINE))


def proof_v0_freeze() -> None:
    inventory = load_json(CONTRACT / "v0-schema-inventory.json")
    check((inventory["supported_minimum"], inventory["supported_maximum"]) == (1, 13), "V0 schema range changed")
    frozen_dir = CONTRACT / "v0" / "schemas"
    migrations = inventory["migrations"]
    check([item["version"] for item in migrations] == list(range(1, 14)), "V0 migration sequence is not exact 1..13")
    with tempfile.TemporaryDirectory(prefix="harness-v1-schema-replay-") as temporary:
        database = Path(temporary) / "replay.db"
        connection = sqlite3.connect(database)
        for item in migrations:
            current = ROOT / "scripts" / "schema" / item["name"]
            frozen = frozen_dir / item["name"]
            check(current.read_bytes() == frozen.read_bytes(), f"frozen schema differs: {item['name']}")
            check(sha256_file(frozen) == item["sha256"], f"frozen schema hash differs: {item['name']}")
            connection.executescript(frozen.read_text(encoding="utf-8"))
            version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            check(version == item["version"], f"schema replay version differs after {item['name']}")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        connection.close()

    categories = load_json(CONTRACT / "v0-data-categories.json")["entries"]
    category_names = [entry["category"] for entry in categories]
    check(len(category_names) == len(set(category_names)), "V0 data category disposition duplicated")
    allowed = set(load_json(CONTRACT / "path-dispositions.json")["allowed_dispositions"])
    check(all(entry["disposition"] in allowed for entry in categories), "V0 data category disposition invalid")
    category_tables = {name.removeprefix("sqlite.table.") for name in category_names if name.startswith("sqlite.table.")}
    check(category_tables == tables, "V0 SQLite tables are not covered one-to-one")

    frozen_commands = noncomment_lines(CONTRACT / "v0-command-paths.txt")
    current_commands = noncomment_lines(ROOT / "tests" / "core" / "harness-command-contract.txt")
    check(frozen_commands == current_commands and len(frozen_commands) == 50, "V0 public command paths changed")
    features = load_json(CONTRACT / "v0-feature-snapshot.json")
    check(features["public_command_path_count"] == len(frozen_commands), "V0 feature command count mismatch")
    cargo = (ROOT / "crates" / "harness-cli" / "Cargo.toml").read_text(encoding="utf-8")
    current_version = re.search(r'^version = "([^"]+)"', cargo, re.MULTILINE)
    check(current_version is not None and current_version.group(1) == features["crate_version"], "V0 crate version snapshot changed")
    source = (ROOT / "crates" / "harness-cli" / "src" / "infrastructure.rs").read_text(encoding="utf-8")
    capability_block = source[source.index("const CAPABILITIES:"):source.index("];", source.index("const CAPABILITIES:"))]
    capabilities = re.findall(r'"([a-z0-9.-]+\.v1)"', capability_block)
    check(capabilities == features["capabilities"], "V0 protocol capability snapshot changed")
    matrix = load_json(CONTRACT / "v0-changeset-operation-matrix.json")
    matrix_ops = {entry["op"] for entry in matrix["operations"]}
    check(matrix_ops == extract_parser_operations(), "V0 changeset operation matrix differs from parser")
    check(all(entry["versions"] == [1, 2] for entry in matrix["operations"]), "operation version freeze changed")
    check('if !(1..=2).contains(&version)' in source, "current parser operation range no longer 1..=2")
    check('header.get("version").and_then(Value::as_i64) != Some(1)' in source, "current changeset header version no longer 1")
    parse_changeset_fixture(POS / "v0-changeset-v1-v2.jsonl", matrix)
    for name in ["v0-changeset-unknown-operation.jsonl", "v0-changeset-unsupported-version.jsonl", "v0-changeset-header-v2.jsonl"]:
        expect_failure(lambda fixture=name: parse_changeset_fixture(NEG / fixture, matrix), name)


def verify_first_bundle(bundle: dict[str, Any], envelope_value: dict[str, Any], anchors: dict[str, Any], label: str) -> tuple[dict[str, bytes], dict[str, bytes], set[str]]:
    domain = anchors["trust_domain"]
    role = "core-release" if domain.endswith("core") else "bridge-release"
    roots, release, revoked = validate_trust_bundle(bundle, domain, role)
    anchor_keys = key_map(anchors["root_keys"])
    check(set(anchor_keys) == set(roots), f"{label}: bootstrap roots differ from bundle")
    check(anchors["exact_bundle_digest"] == canonical_digest(bundle), f"{label}: first bundle pin mismatch")
    domain_tag = f"{domain}-trust-bundle-v1"
    root_role = "core-root" if domain.endswith("core") else "bridge-root"
    verify_envelope(bundle, envelope_value, domain_tag, anchor_keys, anchors["root_threshold"], domain, root_role, 1)
    return roots, release, revoked


def freshness_accepts(index: dict[str, Any], mark: dict[str, Any],
                      authorization: dict[str, Any] | None = None,
                      active_root_bundle_sequence: int | None = None) -> bool:
    digest = canonical_digest(index)
    sequence = index["sequence"]
    if sequence > mark["sequence"]:
        return True
    if sequence == mark["sequence"]:
        return digest == mark["digest"]
    if authorization is None:
        return False
    return (active_root_bundle_sequence is not None
            and authorization["root_bundle_sequence"] == active_root_bundle_sequence
            and authorization["trust_domain"] == index["trust_domain"]
            and authorization["role"] == index["role"]
            and authorization["authorized_sequence"] == sequence
            and authorization["authorized_digest"] == digest)


def proof_trust() -> None:
    anchors = load_json(POS / "test-bootstrap-anchors.json")
    check(anchors["test_fixture_notice"] == "UNSAFE-TEST-ONLY-NOT-A-RELEASE-TRUST-BUNDLE", "test anchor warning missing")
    core_bundle = load_json(POS / "core-trust-bundle.json")
    bridge_bundle = load_json(POS / "bridge-trust-bundle.json")
    core_roots, core_release, _ = verify_first_bundle(core_bundle, load_json(POS / "core-trust-bundle.signatures.json"), anchors["core"], "core")
    bridge_roots, bridge_release, _ = verify_first_bundle(bridge_bundle, load_json(POS / "bridge-trust-bundle.signatures.json"), anchors["bridge"], "bridge")
    check(set(core_roots) | set(core_release), "core trust bundle empty")
    check((set(core_roots) | set(core_release)).isdisjoint(set(bridge_roots) | set(bridge_release)), "core/bridge key crossover")

    core_index = load_json(POS / "core-payload-index.json")
    bridge_index = load_json(POS / "bridge-payload-index.json")
    validate_payload_index(core_index, "repository-harness-core", "core-release")
    validate_payload_index(bridge_index, "repository-harness-bridge", "bridge-release")
    verify_envelope(core_index, load_json(POS / "core-payload-index.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 42)
    verify_envelope(bridge_index, load_json(POS / "bridge-payload-index.signatures.json"), "repository-harness-bridge-payload-index-v1", bridge_release, 2, "repository-harness-bridge", "bridge-release", 7)
    reencoded = load_json(POS / "core-payload-index-reencoded.json")
    check(reencoded == core_index and canonical_digest(reencoded) == canonical_digest(core_index), "benign JSON reencoding changed canonical identity")
    verify_envelope(reencoded, load_json(POS / "core-payload-index.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 42)

    expect_failure(lambda: load_json(NEG / "duplicate-key-index.json"), "duplicate JSON member")
    unicode_index = load_json(NEG / "unicode-reencoded-index.json")
    expect_failure(lambda: validate_payload_index(unicode_index, "repository-harness-core", "core-release"), "Unicode non-NFC reencoding")
    expect_failure(lambda: verify_envelope(core_index, load_json(NEG / "bad-threshold.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 42), "one signature threshold")
    expect_failure(lambda: verify_envelope(core_index, load_json(NEG / "bad-signature.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 42), "bad signature")
    expect_failure(lambda: verify_envelope(core_index, load_json(NEG / "key-crossover.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 42), "bridge keys on core index")
    expect_failure(lambda: verify_envelope(core_index, load_json(NEG / "key-role-crossover.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 42), "core root keys on core release index")
    expect_failure(lambda: verify_envelope(core_index, load_json(NEG / "unknown-key.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 42), "unknown release key does not count")

    for name in ["ed25519-identity.json", "ed25519-order-two.json", "ed25519-zero-scalar.json"]:
        vector = load_json(NEG / name)
        public_key = base64.b64decode(vector["public_key_base64"], validate=True)
        message = base64.b64decode(vector["message_base64"], validate=True)
        signature = base64.b64decode(vector["signature_base64"], validate=True)
        check(not ed25519_verify(public_key, message, signature), f"strict Ed25519 accepted {vector['case']}")
    forged_keys_value = load_json(NEG / "forged-2-of-3-keys.json")
    forged_keys: dict[str, bytes] = {}
    for entry in forged_keys_value["keys"]:
        raw = base64.b64decode(entry["public_key_base64"], validate=True)
        check(entry["key_id"] == "ed25519-sha256:" + sha256_bytes(raw), "forged fixture key ID mismatch")
        forged_keys[entry["key_id"]] = raw
    expect_failure(lambda: verify_envelope(core_index, load_json(NEG / "forged-2-of-3.signatures.json"), "repository-harness-payload-index-v1", forged_keys, 2, "repository-harness-core", "core-release", 42), "small-order forged 2-of-3 envelope")

    high_water = load_json(POS / "high-water-marks.json")
    marks = {(entry["trust_domain"], entry["role"]): entry for entry in high_water["marks"]}
    core_mark = marks[("repository-harness-core", "core-release")]
    bridge_mark = marks[("repository-harness-bridge", "bridge-release")]
    check(freshness_accepts(core_index, core_mark), "equal sequence/digest must be idempotent")
    changed_same_sequence = dict(core_index)
    changed_same_sequence["release"] = "different"
    check(not freshness_accepts(changed_same_sequence, core_mark), "equal sequence/different digest must fail")
    freeze = load_json(NEG / "freeze-payload-index.json")
    verify_envelope(freeze, load_json(NEG / "freeze-payload-index.signatures.json"), "repository-harness-payload-index-v1", core_release, 2, "repository-harness-core", "core-release", 41)
    check(not freshness_accepts(freeze, core_mark), "release signatures must not bypass freeze protection")
    rollback = load_json(POS / "authorized-rollback.json")
    verify_envelope(rollback, load_json(POS / "authorized-rollback.signatures.json"), "repository-harness-core-rollback-authorization-v1", core_roots, 2, "repository-harness-core", "core-root", 1)
    check(not freshness_accepts(freeze, core_mark, rollback), "rollback without an active trusted root-bundle sequence must fail")
    check(freshness_accepts(freeze, core_mark, rollback, core_bundle["sequence"]), "exact root-authorized rollback must pass")
    wrong = load_json(NEG / "wrong-rollback.json")
    verify_envelope(wrong, load_json(NEG / "wrong-rollback.signatures.json"), "repository-harness-core-rollback-authorization-v1", core_roots, 2, "repository-harness-core", "core-root", 1)
    check(not freshness_accepts(freeze, core_mark, wrong, core_bundle["sequence"]), "wrong rollback digest must fail")
    wrong_root_sequence = load_json(NEG / "wrong-root-bundle-sequence-rollback.json")
    validate_schema(wrong_root_sequence, load_json(SCHEMAS / "rollback-authorization-v1.schema.json"))
    verify_envelope(wrong_root_sequence, load_json(NEG / "wrong-root-bundle-sequence-rollback.signatures.json"), "repository-harness-core-rollback-authorization-v1", core_roots, 2, "repository-harness-core", "core-root", wrong_root_sequence["root_bundle_sequence"])
    check(not freshness_accepts(freeze, core_mark, wrong_root_sequence, core_bundle["sequence"]), "rollback authorization for a non-active root bundle sequence must fail")
    check(high_water["first_install"]["core_exact_digest"] == canonical_digest(core_index), "offline core exact pin mismatch")
    check(bridge_index["sequence"] >= high_water["first_install"]["bridge_minimum_sequence"] and freshness_accepts(bridge_index, bridge_mark), "offline bridge minimum pin mismatch")

    revocation = load_json(POS / "revocation-trust-bundle.json")
    check(revocation["sequence"] > core_bundle["sequence"] and revocation["previous_bundle_sha256"] == canonical_digest(core_bundle), "revocation bundle freshness/chain")
    verify_envelope(revocation, load_json(POS / "revocation-trust-bundle.signatures.json"), "repository-harness-core-trust-bundle-v1", core_roots, 2, "repository-harness-core", "core-root", 2)
    _, revocation_release, revoked = validate_trust_bundle(revocation, "repository-harness-core", "core-release")
    updated = load_json(POS / "post-revocation-payload-index.json")
    verify_envelope(updated, load_json(POS / "post-revocation-payload-index.signatures.json"), "repository-harness-payload-index-v1", revocation_release, 2, "repository-harness-core", "core-release", 43, revoked)
    expect_failure(lambda: verify_envelope(core_index, load_json(NEG / "revoked-payload-index.signatures.json"), "repository-harness-payload-index-v1", revocation_release, 2, "repository-harness-core", "core-release", 42, revoked), "revoked signer threshold")

    rotation = load_json(POS / "root-rotation-trust-bundle.json")
    rotation_envelope = load_json(POS / "root-rotation-trust-bundle.signatures.json")
    check(rotation["sequence"] > revocation["sequence"] and rotation["previous_bundle_sha256"] == canonical_digest(revocation), "rotation bundle chain")
    new_roots, _, _ = validate_trust_bundle(rotation, "repository-harness-core", "core-release")
    old_valid = verify_envelope(rotation, rotation_envelope, "repository-harness-core-trust-bundle-v1", core_roots, 2, "repository-harness-core", "core-root-rotation", 3)
    new_valid = verify_envelope(rotation, rotation_envelope, "repository-harness-core-trust-bundle-v1", new_roots, 2, "repository-harness-core", "core-root-rotation", 3)
    check(len(old_valid) >= 2 and len(new_valid) >= 2, "root rotation needs old and new thresholds")
    old_only = dict(rotation_envelope)
    old_only["signatures"] = [signature for signature in rotation_envelope["signatures"] if signature["key_id"] in core_roots]
    new_only = dict(rotation_envelope)
    new_only["signatures"] = [signature for signature in rotation_envelope["signatures"] if signature["key_id"] in new_roots]
    expect_failure(lambda: verify_envelope(rotation, old_only, "repository-harness-core-trust-bundle-v1", new_roots, 2, "repository-harness-core", "core-root-rotation", 3), "rotation old threshold only")
    expect_failure(lambda: verify_envelope(rotation, new_only, "repository-harness-core-trust-bundle-v1", core_roots, 2, "repository-harness-core", "core-root-rotation", 3), "rotation new threshold only")

    availability = load_json(POS / "availability-receipt.json")
    policy = load_json(CONTRACT / "compatibility-policy.json")
    validate_availability_receipt(availability, policy)
    verify_envelope(availability, load_json(POS / "availability-receipt.signatures.json"), "repository-harness-bridge-availability-receipt-v1", bridge_release, 2, "repository-harness-bridge", "bridge-release", 8)
    for name in ["availability-gap-over-seven.json", "availability-decreasing.json", "availability-wrong-month.json", "availability-missing-start-coverage.json", "availability-missing-end-coverage.json", "availability-naive-timestamp.json", "availability-incomplete-set.json", "availability-missing-platform.json"]:
        expect_failure(lambda fixture=name: validate_availability_receipt(load_json(NEG / fixture), policy), name)
    trust_cases = load_json(FIXTURES / "trust-cases.json")
    check(len(trust_cases["positive"]) >= 10 and len(trust_cases["negative"]) >= 24, "trust case inventory incomplete")


def read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def capture_anchored(root_descriptor: int, relative: str,
                     hook: Callable[[str, int], None] | None = None) -> tuple[bytes, tuple[int, int], int, str]:
    """Capture one file through a pinned root fd with no pathname reopen."""
    safe_path(relative)
    parts = relative.split("/")
    root_before = os.fstat(root_descriptor)
    descriptors = [os.dup(root_descriptor)]
    components: list[tuple[int, str, int, tuple[int, int]]] = []
    try:
        parent = descriptors[0]
        for index, part in enumerate(parts):
            final = index == len(parts) - 1
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            if not final:
                flags |= getattr(os, "O_DIRECTORY", 0)
            child = os.open(part, flags, dir_fd=parent)
            descriptors.append(child)
            opened = os.fstat(child)
            check(not stat.S_ISLNK(opened.st_mode), f"source component is a symlink: {relative}")
            if final:
                check(stat.S_ISREG(opened.st_mode), f"capture source is not a regular file: {relative}")
            else:
                check(stat.S_ISDIR(opened.st_mode), f"capture ancestor is not a directory: {relative}")
            components.append((parent, part, child, (opened.st_dev, opened.st_ino)))
            if hook is not None:
                hook("final-open" if final else "ancestor-open", index)
            parent = child

        final_descriptor = descriptors[-1]
        observations: list[tuple[tuple[int, int], int, str]] = []
        copied = b""
        for phase in ("pre", "copy", "post"):
            data = read_descriptor(final_descriptor)
            observed = os.fstat(final_descriptor)
            observation = ((observed.st_dev, observed.st_ino), observed.st_size, sha256_bytes(data))
            check(observed.st_size == len(data), f"{phase} capture size differs from handle: {relative}")
            observations.append(observation)
            if phase == "copy":
                copied = data
            if hook is not None:
                hook(f"after-{phase}", len(parts) - 1)
        check(observations[0] == observations[1] == observations[2], f"pre/copy/post identity-size-hash differs: {relative}")

        for parent_descriptor, part, _child, opened_identity in components:
            current = os.stat(part, dir_fd=parent_descriptor, follow_symlinks=False)
            check(not stat.S_ISLNK(current.st_mode), f"source component became a symlink: {relative}")
            check((current.st_dev, current.st_ino) == opened_identity, f"source component identity changed during capture: {relative}")
        root_after = os.fstat(root_descriptor)
        check((root_before.st_dev, root_before.st_ino) == (root_after.st_dev, root_after.st_ino), "pinned capture root identity changed")
        identity, size, digest = observations[1]
        return copied, identity, size, digest
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def proof_paths_and_swaps() -> None:
    cases = load_json(FIXTURES / "path-cases.json")
    for path in cases["positive"]:
        safe_path(path, allow_harness=True)
    for entry in cases["negative"]:
        expect_failure(lambda value=entry["path"]: safe_path(value, allow_harness=True), entry["rule"])
    for collision in cases["collision_sets"]:
        keys = [unicodedata.normalize("NFC", path).casefold() for path in collision["paths"]]
        check(len(set(keys)) < len(keys), f"collision fixture does not collide: {collision['rule']}")

    with tempfile.TemporaryDirectory(prefix="harness-v1-path-fixture-") as temporary:
        root = Path(temporary)
        (root / "real").mkdir()
        (root / "real" / "file").write_text("safe", encoding="utf-8")
        (root / "final-link").symlink_to(root / "real" / "file")
        (root / "ancestor-link").symlink_to(root / "real", target_is_directory=True)
        root_descriptor = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            expect_failure(lambda: capture_anchored(root_descriptor, "final-link"), "symlink final component")
            expect_failure(lambda: capture_anchored(root_descriptor, "ancestor-link/file"), "symlink ancestor")

            final_swap = root / "final-swap"
            final_swap.write_text("original", encoding="utf-8")
            final_swapped = False

            def swap_final(phase: str, _index: int) -> None:
                nonlocal final_swapped
                if phase == "final-open" and not final_swapped:
                    final_swapped = True
                    final_swap.rename(root / "final-original")
                    final_swap.write_text("original", encoding="utf-8")

            expect_failure(lambda: capture_anchored(root_descriptor, "final-swap", swap_final), "final component swap through pinned root")

            ancestor = root / "ancestor-swap"
            ancestor.mkdir()
            (ancestor / "file").write_text("original", encoding="utf-8")
            ancestor_swapped = False

            def swap_ancestor(phase: str, index: int) -> None:
                nonlocal ancestor_swapped
                if phase == "ancestor-open" and index == 0 and not ancestor_swapped:
                    ancestor_swapped = True
                    ancestor.rename(root / "ancestor-original")
                    ancestor.mkdir()
                    (ancestor / "file").write_text("replacement", encoding="utf-8")

            expect_failure(lambda: capture_anchored(root_descriptor, "ancestor-swap/file", swap_ancestor), "ancestor component swap through pinned root")

            mutating = root / "mutating"
            mutating.write_text("before!", encoding="utf-8")
            mutated = False

            def mutate_source(phase: str, _index: int) -> None:
                nonlocal mutated
                if phase == "after-pre" and not mutated:
                    mutated = True
                    mutating.write_text("after!!", encoding="utf-8")

            expect_failure(lambda: capture_anchored(root_descriptor, "mutating", mutate_source), "source content mutation during capture")
        finally:
            os.close(root_descriptor)


def proof_wal_capture() -> None:
    fixture = FIXTURES / "v0-capture" / "wal-only"
    source = fixture / "source"
    expected = load_json(fixture / "expected.json")
    for name, digest in expected["files"].items():
        check(sha256_file(source / name) == digest, f"committed V0 fixture hash differs: {name}")

    with tempfile.TemporaryDirectory(prefix="harness-v1-v0-capture-") as temporary:
        temporary_path = Path(temporary)
        readonly = temporary_path / "readonly-source"
        readonly.mkdir()
        for name in expected["files"]:
            target = readonly / name
            target.write_bytes((source / name).read_bytes())
            target.chmod(0o444)
        captured: dict[str, bytes] = {}
        identities: dict[str, tuple[int, int]] = {}
        source_descriptor = os.open(readonly, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            for name, digest in expected["files"].items():
                data, identity, size, copied_digest = capture_anchored(source_descriptor, name)
                check(copied_digest == digest and size == len(data), f"capture equality differs: {name}")
                captured[name] = data
                identities[name] = identity
        finally:
            os.close(source_descriptor)
        check(len(set(identities.values())) == len(identities), "capture identities are ambiguous")

        mutable = temporary_path / "mutable-source"
        mutable.mkdir()
        for name in expected["files"]:
            (mutable / name).write_bytes((source / name).read_bytes())

        def mutation_failure(name: str, replacement: bool) -> None:
            root_descriptor = os.open(mutable, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
            changed = False

            def change(phase: str, _index: int) -> None:
                nonlocal changed
                trigger = "final-open" if replacement else "after-pre"
                if phase != trigger or changed:
                    return
                changed = True
                target = mutable / name
                if replacement:
                    target.rename(mutable / f"{name}.replaced")
                    target.write_bytes((source / name).read_bytes())
                else:
                    value = bytearray(target.read_bytes())
                    value[len(value) // 2] ^= 1
                    target.write_bytes(value)

            try:
                capture_anchored(root_descriptor, name, change)
            finally:
                os.close(root_descriptor)

        expect_failure(lambda: mutation_failure("harness.db", False), "main database mutation during capture")
        (mutable / "harness.db").write_bytes((source / "harness.db").read_bytes())
        expect_failure(lambda: mutation_failure("harness.db-wal", False), "WAL mutation during capture")
        (mutable / "harness.db-wal").write_bytes((source / "harness.db-wal").read_bytes())
        expect_failure(lambda: mutation_failure("harness.db-wal", True), "WAL replacement during capture")

        main_only = temporary_path / "main-only.db"
        main_only.write_bytes(captured["harness.db"])
        connection = sqlite3.connect(main_only)
        count_without_wal = connection.execute("SELECT COUNT(*) FROM wal_proof").fetchone()[0]
        connection.close()
        check(count_without_wal == 0, "fixture row is not WAL-only")

        stage = temporary_path / "stage"
        stage.mkdir()
        (stage / "harness.db").write_bytes(captured["harness.db"])
        (stage / "harness.db-wal").write_bytes(captured["harness.db-wal"])
        check(sha256_file(stage / "harness.db") == expected["files"]["harness.db"], "staged DB copy digest differs")
        check(sha256_file(stage / "harness.db-wal") == expected["files"]["harness.db-wal"], "staged WAL copy digest differs")
        check(not (stage / "harness.db-shm").exists(), "SHM must not be staged as recovery input")
        recovered = sqlite3.connect(stage / "harness.db")
        row = list(recovered.execute("SELECT id, value FROM wal_proof"))[0]
        check(list(row) == expected["expected_row"], "staged DB+WAL lost committed row")
        standalone = temporary_path / "standalone-backup.db"
        backup = sqlite3.connect(standalone)
        recovered.backup(backup)
        backup.close()
        recovered.close()
        authority = sqlite3.connect(standalone)
        backed_up = list(authority.execute("SELECT id, value FROM wal_proof"))[0]
        authority.close()
        check(list(backed_up) == expected["expected_row"], "standalone logical backup lost WAL-only row")
        for name, digest in expected["files"].items():
            check(sha256_file(readonly / name) == digest, f"read-only source was modified: {name}")


def proof_archive_and_policy() -> None:
    manifest = load_json(POS / "archive" / "manifest.json")
    archive = POS / "archive" / "conversion.age"
    tampered_manifest = load_json(NEG / "archive" / "manifest.json")
    tampered = NEG / "archive" / "conversion.age"
    check(manifest["confidentiality_mode"] == "encrypted-age-x25519" and manifest["recipient_fingerprints"], "default archive encryption/recipient missing")
    check(sha256_file(archive) == manifest["archive_sha256"], "valid archive digest mismatch")
    expect_failure(lambda: check(sha256_file(tampered) == tampered_manifest["archive_sha256"], "archive digest mismatch"), "tampered archive")
    policy = load_json(CONTRACT / "compatibility-policy.json")
    check(policy["compatibility_window"] == {"start": "2027-01-01T00:00:00Z", "end_inclusive": "2027-12-31T23:59:59Z", "minimum_supported_days_if_shifted": 365}, "Decision 0012 window changed")
    check(policy["local_archives"]["retention"] == "indefinite" and not policy["local_archives"]["automatic_delete_overwrite_truncate_relocate"], "archive custody/retention changed")
    check(policy["bridge_assets"]["availability_check_max_interval_days"] == 7 and policy["bridge_assets"]["signed_receipt_interval"] == "calendar-month", "weekly/monthly availability obligation changed")
    check(policy["bridge_assets"]["supported_platforms"] == [entry["platform"] for entry in EXPECTED_RELEASE_PLATFORMS], "availability supported platform set changed")
    check(set(policy["bridge_assets"]["platform_scoped_categories"]) <= set(policy["bridge_assets"]["complete_set"]), "availability platform-scoped categories escape complete_set")
    check(policy["bridge_assets"]["retained_through_inclusive"] == "2028-06-30T23:59:59Z", "bridge retention deadline changed")
    check(policy["phase_8"]["eligible_no_earlier_than"] == "2028-01-01T00:00:00Z" and len(policy["phase_8"]["requires"]) == 8, "Phase 8 gates changed")
    bootstrap = load_json(CONTRACT / "bootstrap-identity.json")
    validate_bootstrap(bootstrap)
    check(bootstrap["production_v1_pipe_to_shell"] == "prohibited" and not bootstrap["adjacent_downloaded_key_is_trust_anchor"], "non-circular bootstrap rule changed")
    check(bootstrap["core"]["protected_workflow"] != bootstrap["bridge"]["protected_workflow"], "core/bridge release workflows must be separate")
    check(bootstrap["github_sigstore_role"] == "bootstrap-and-supplemental-not-payload-trust-root", "provenance trust role changed")
    for name in ["bootstrap-added-step.json", "bootstrap-reordered.json", "bootstrap-domain-mismatch.json", "bootstrap-tag-mismatch.json", "bootstrap-sequence-mismatch.json", "bootstrap-role-crossover.json", "bootstrap-workflow-state-mismatch.json", "bootstrap-workflow-path-mismatch.json", "bootstrap-unknown-field.json"]:
        expect_failure(lambda fixture=name: validate_bootstrap(load_json(NEG / fixture)), name)
    for surface in ("core", "bridge"):
        with tempfile.TemporaryDirectory(prefix=f"harness-v1-{surface}-workflow-") as temporary:
            temporary_root = Path(temporary)
            workflow_path = bootstrap[surface]["protected_workflow"].split("@", 1)[0]
            reserved_workflow = temporary_root / workflow_path
            reserved_workflow.parent.mkdir(parents=True)
            reserved_workflow.write_text("# UNSAFE TEST ONLY reserved workflow\n", encoding="utf-8")
            expect_failure(lambda root=temporary_root: validate_bootstrap(bootstrap, root), f"{surface} reserved workflow appeared in Phase 1")


def proof_docs_and_scope() -> None:
    required_docs = [
        ROOT / "docs" / "decisions" / "0013-v1-security-and-v0-capture-contract.md",
        *(ROOT / "docs" / "contracts" / "v1" / name for name in ["README.md", "manifest-and-state.md", "command-grammars.md", "payload-trust.md", "scaffold-and-audit.md", "compatibility-conversion-and-retirement.md", "v0-compatibility.md"]),
        *(ROOT / "docs" / "stories" / "US-106-v1-phase1-contracts-and-release-inventory" / name for name in ["overview.md", "design.md", "execplan.md", "validation.md"]),
    ]
    for path in required_docs:
        check(path.is_file() and path.stat().st_size > 100, f"required Phase 1 document missing/incomplete: {path.relative_to(ROOT)}")
    decision = required_docs[0].read_text(encoding="utf-8")
    for phrase in ["2-of-3", "RFC 8785", "small-order", "pipe-to-shell", "age/X25519", "WAL", "SHM", "604800", "Phase 8"]:
        check(phrase in decision, f"Decision 0013 omits accepted contract: {phrase}")
    native_core = ROOT / "scripts" / "bin" / ("harness.exe" if os.name == "nt" else "harness")
    check(native_core.is_file(), f"Phase 2 live core binary is missing: {native_core.relative_to(ROOT)}")
    for forbidden_runtime in [ROOT / "scripts" / "bin" / "harness-v0-migrate", ROOT / "scripts" / "bin" / "harness-v0-migrate.exe"]:
        check(not forbidden_runtime.exists(), f"Phase 4 bridge binary entered Phase 2: {forbidden_runtime.relative_to(ROOT)}")


def main() -> None:
    os.chdir(ROOT)
    proof("closed schemas, manifest fields, and deterministic envelopes", proof_schemas_and_examples)
    proof("core-live/bridge-absent six/seven-command grammar and source/CLI parity", proof_grammar)
    proof("one-to-one current install/release path ledger and core exclusions", proof_path_inventory)
    proof("exact V0 schemas 1-13, tables, commands, capabilities, and parser matrix", proof_v0_freeze)
    proof("Ed25519 thresholds, domains, freshness, rollback, revocation, and rotation", proof_trust)
    proof("safe paths, normalization/case collisions, symlinks, and path swaps", proof_paths_and_swaps)
    proof("read-only no-follow V0 capture and WAL-only standalone recovery", proof_wal_capture)
    proof("archive tamper, confidentiality, availability, bootstrap, and Phase 8 policy", proof_archive_and_policy)
    proof("Decision 0013, Phase 1 contracts, live core, and bridge absence", proof_docs_and_scope)
    print(f"V1 Phase 1 contract verification passed ({PASS_COUNT} proof groups)")


if __name__ == "__main__":
    try:
        main()
    except ContractError as error:
        print(f"V1 Phase 1 contract verification failed: {error}", file=os.sys.stderr)
        raise SystemExit(1) from error

#!/usr/bin/env python3
"""Shared closed-data helpers for non-production V1 build receipts."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "release/contracts/v1/schemas/build-receipt-v1.schema.json"
RECEIPT_NAME = "build-receipt.json"
WORKFLOW_PATH = ".github/workflows/harness-v1-release.yml"
CARGO_LOCK_PATH = "Cargo.lock"
COMMAND_BINDING_PATH = "release/contracts/v1/command-implementation-binding.json"
COMMAND_GRAMMAR_PATH = "release/contracts/v1/command-grammars.json"

PLATFORMS = OrderedDict(
    (
        ("macos-arm64", ("aarch64-apple-darwin", "macos-15", "harness-macos-arm64")),
        ("macos-x64", ("x86_64-apple-darwin", "macos-15-intel", "harness-macos-x64")),
        ("linux-x64", ("x86_64-unknown-linux-gnu", "ubuntu-24.04", "harness-linux-x64")),
        ("linux-arm64", ("aarch64-unknown-linux-gnu", "ubuntu-24.04-arm", "harness-linux-arm64")),
        ("windows-x64", ("x86_64-pc-windows-msvc", "windows-latest", "harness-windows-x64.exe")),
    )
)

BLOCKERS = [
    "deferred-phase6-live-p0-p7-evidence-pending",
    "five-platform-acceptance-pending",
    "installer-proof-pending",
    "full-direct-binary-proof-pending",
    "authenticated-provenance-pending",
]


class ReceiptError(RuntimeError):
    """Raised when build-receipt input or evidence is unsafe or inconsistent."""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptError(message)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReceiptError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def parse_json_bytes(payload: bytes, label: str) -> Any:
    try:
        return json.loads(payload.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except ReceiptError:
        raise
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ReceiptError(f"invalid JSON bytes: {label}") from error


def load_json(path: Path) -> Any:
    try:
        return parse_json_bytes(path.read_bytes(), str(path))
    except OSError as error:
        raise ReceiptError(f"cannot read JSON file: {path}") from error


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise ReceiptError(f"cannot hash file: {path}") from error
    return digest.hexdigest()


def type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    check(reference.startswith("#/"), f"unsupported schema reference: {reference}")
    value: Any = root
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        check(isinstance(value, dict) and token in value, f"unresolved schema reference: {reference}")
        value = value[token]
    check(isinstance(value, dict), f"schema reference is not an object: {reference}")
    return value


def validate_schema(
    instance: Any,
    contract: dict[str, Any],
    root: dict[str, Any],
    location: str = "$",
) -> None:
    if "$ref" in contract:
        validate_schema(instance, resolve_ref(root, contract["$ref"]), root, location)
    for branch in contract.get("allOf", []):
        validate_schema(instance, branch, root, location)
    if "const" in contract:
        check(instance == contract["const"], f"{location}: const mismatch")
    if "enum" in contract:
        check(instance in contract["enum"], f"{location}: value outside enum")
    if "type" in contract:
        expected = contract["type"] if isinstance(contract["type"], list) else [contract["type"]]
        check(any(type_matches(instance, item) for item in expected), f"{location}: wrong JSON type")
    if isinstance(instance, dict):
        required = set(contract.get("required", []))
        check(required <= set(instance), f"{location}: missing {sorted(required - set(instance))}")
        properties = contract.get("properties", {})
        if contract.get("additionalProperties") is False:
            check(set(instance) <= set(properties), f"{location}: unknown fields {sorted(set(instance) - set(properties))}")
        for key, value in instance.items():
            if key in properties:
                validate_schema(value, properties[key], root, f"{location}.{key}")
    if isinstance(instance, list):
        if "minItems" in contract:
            check(len(instance) >= contract["minItems"], f"{location}: too few items")
        if "maxItems" in contract:
            check(len(instance) <= contract["maxItems"], f"{location}: too many items")
        prefix = contract.get("prefixItems", [])
        for index, item_contract in enumerate(prefix):
            if index < len(instance):
                validate_schema(instance[index], item_contract, root, f"{location}[{index}]")
        items = contract.get("items")
        if items is False:
            check(len(instance) <= len(prefix), f"{location}: extra array items")
        elif isinstance(items, dict):
            for index, value in enumerate(instance[len(prefix) :], start=len(prefix)):
                validate_schema(value, items, root, f"{location}[{index}]")
    if isinstance(instance, str):
        if "minLength" in contract:
            check(len(instance) >= contract["minLength"], f"{location}: string is empty")
        if "pattern" in contract:
            check(re.fullmatch(contract["pattern"], instance) is not None, f"{location}: pattern mismatch")
    if isinstance(instance, int) and not isinstance(instance, bool) and "minimum" in contract:
        check(instance >= contract["minimum"], f"{location}: below minimum")


def assert_closed_schema(node: Any, location: str = "$schema") -> None:
    if isinstance(node, dict):
        if node.get("type") == "object":
            check(node.get("additionalProperties") is False, f"{location}: object schema is not closed")
        for key, value in node.items():
            assert_closed_schema(value, f"{location}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            assert_closed_schema(value, f"{location}[{index}]")


def validate_contract(document: Any) -> dict[str, Any]:
    schema = load_json(SCHEMA_PATH)
    check(isinstance(schema, dict), "build-receipt schema is not an object")
    check(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "build-receipt schema is not Draft 2020-12")
    assert_closed_schema(schema)
    check(isinstance(document, dict), "build receipt is not an object")
    validate_schema(document, schema, schema, "build receipt")
    return document


def relative_filename(value: str, field: str) -> str:
    path = PurePosixPath(value)
    check(not path.is_absolute(), f"{field}: absolute path is prohibited")
    check(len(path.parts) == 1 and path.parts[0] not in {"", ".", ".."}, f"{field}: traversal or nested path is prohibited")
    check(str(path) == value and "\\" not in value, f"{field}: path is not canonical POSIX form")
    return value


def reject_command_fields(value: Any, location: str = "$receipt") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            check(key not in {"command", "commands"}, f"{location}: command fields are prohibited")
            reject_command_fields(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_command_fields(child, f"{location}[{index}]")


def exact_core_help_bytes(grammar_document: dict[str, Any]) -> bytes:
    check(set(grammar_document) >= {"schema", "core"}, "command grammar contract is incomplete")
    core = grammar_document["core"]
    check(isinstance(core, dict), "core command grammar is not an object")
    expected = ["install", "update", "audit", "scaffold", "status", "version"]
    check(core.get("top_level") == expected, "core help does not have the exact six-command order")
    commands = core.get("commands")
    check(isinstance(commands, list) and [item.get("name") for item in commands if isinstance(item, dict)] == expected, "core help command records do not match the exact six-command order")
    return (json.dumps(core, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")

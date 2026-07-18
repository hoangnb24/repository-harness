#!/usr/bin/env python3
"""Verify the closed, non-promotable V1 Phase 7 release-proof contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT
    / "release"
    / "contracts"
    / "v1"
    / "schemas"
    / "phase7-release-proof-v1.schema.json"
)
DEFAULT_FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "v1-phase7"
DEFAULT_EVIDENCE = DEFAULT_FIXTURE_ROOT / "phase7-release-proof.json"

PLATFORMS = {
    "macos-arm64": ("aarch64-apple-darwin", "macos-15"),
    "macos-x64": ("x86_64-apple-darwin", "macos-15-intel"),
    "linux-x64": ("x86_64-unknown-linux-gnu", "ubuntu-24.04"),
    "linux-arm64": ("aarch64-unknown-linux-gnu", "ubuntu-24.04-arm"),
    "windows-x64": ("x86_64-pc-windows-msvc", "windows-latest"),
}
FIXTURE_CASES = [
    "fresh",
    "brownfield",
    "nested-instructions",
    "docs-only",
    "monorepo",
    "spaces-unicode",
    "lf",
    "crlf",
    "custom-update",
    "bridge",
]
FIXTURE_IDENTITY_BINDINGS = {
    "v1_cli_sha256": ROOT / "release/contracts/v1/command-implementation-binding.json",
    "template_sha256": ROOT / "scripts/harness-install-files.txt",
    "payload_index_sha256": ROOT / "tests/fixtures/v1-phase2/current-core-payload-index.json",
    "bridge_sha256": ROOT / "release/contracts/v1/bridge-release-artifacts.json",
    "build_input_sha256": ROOT / "release/contracts/v1/release-artifacts.json",
}
BLOCKERS = [
    "deferred-phase6-live-p0-p7-evidence-pending",
    "phase7-five-platform-results-pending",
]
FIXTURE_SOURCE_REVISION = "9da1c49e497b0fedcbd87c877da1186c8a6a582f"


class VerificationError(RuntimeError):
    pass


class PendingPromotion(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise VerificationError(f"duplicate JSON object key: {key}")
        document[key] = value
    return document


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
        )
    except VerificationError:
        raise
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
        raise VerificationError(f"cannot hash evidence member: {path}") from error
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )


def type_matches(instance: Any, expected: str) -> bool:
    return {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
        "boolean": isinstance(instance, bool),
        "null": instance is None,
    }.get(expected, False)


def resolve_ref(contract_root: dict[str, Any], reference: str) -> dict[str, Any]:
    check(reference.startswith("#/"), f"schema uses unsupported reference: {reference}")
    value: Any = contract_root
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        check(isinstance(value, dict) and token in value, f"unresolved schema reference: {reference}")
        value = value[token]
    check(isinstance(value, dict), f"schema reference is not an object: {reference}")
    return value


def validate_schema(
    instance: Any,
    contract: dict[str, Any],
    contract_root: dict[str, Any],
    location: str = "$",
) -> None:
    if "$ref" in contract:
        validate_schema(instance, resolve_ref(contract_root, contract["$ref"]), contract_root, location)
        return
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
                validate_schema(value, properties[key], contract_root, f"{location}.{key}")
    if isinstance(instance, list):
        if "minItems" in contract:
            check(len(instance) >= contract["minItems"], f"{location}: too few items")
        if "maxItems" in contract:
            check(len(instance) <= contract["maxItems"], f"{location}: too many items")
        if contract.get("uniqueItems") is True:
            check(
                all(item not in instance[:index] for index, item in enumerate(instance)),
                f"{location}: duplicate array items",
            )
        prefix_items = contract.get("prefixItems", [])
        for index, item_contract in enumerate(prefix_items):
            if index < len(instance):
                validate_schema(instance[index], item_contract, contract_root, f"{location}[{index}]")
        item_contract = contract.get("items")
        if item_contract is False:
            check(len(instance) <= len(prefix_items), f"{location}: extra array items")
        elif isinstance(item_contract, dict):
            for index, value in enumerate(instance[len(prefix_items) :], start=len(prefix_items)):
                validate_schema(value, item_contract, contract_root, f"{location}[{index}]")
    if isinstance(instance, str):
        if "minLength" in contract:
            check(len(instance) >= contract["minLength"], f"{location}: string is empty")
        if "pattern" in contract:
            check(re.fullmatch(contract["pattern"], instance) is not None, f"{location}: pattern mismatch")


def assert_closed_schema(node: Any, location: str = "$schema") -> None:
    if isinstance(node, dict):
        if node.get("type") == "object":
            check(node.get("additionalProperties") is False, f"{location}: object schema is not closed")
        for key, value in node.items():
            assert_closed_schema(value, f"{location}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            assert_closed_schema(value, f"{location}[{index}]")


def relative_path(value: str, field: str) -> PurePosixPath:
    candidate = PurePosixPath(value)
    check(not candidate.is_absolute(), f"{field}: absolute path is prohibited")
    check(all(part not in {"", ".", ".."} for part in candidate.parts), f"{field}: traversal is prohibited")
    check(str(candidate) == value and "\\" not in value, f"{field}: path is not canonical POSIX form")
    return candidate


def contained_file(root: Path, value: str, field: str) -> Path:
    relative = relative_path(value, field)
    candidate = root.joinpath(*relative.parts)
    check(candidate.is_file() and not candidate.is_symlink(), f"{field}: missing or unsafe file")
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise VerificationError(f"{field}: file escaped fixture root") from error
    return candidate


def exact_files(root: Path) -> set[str]:
    check(root.is_dir() and not root.is_symlink(), f"fixture directory is missing or unsafe: {root}")
    members: set[str] = set()
    for member in root.rglob("*"):
        check(not member.is_symlink(), f"fixture tree contains a symlink: {member}")
        if member.is_file():
            members.add(member.relative_to(root).as_posix())
    return members


def validate_fixture_matrix(document: dict[str, Any], fixture_root: Path) -> None:
    fixtures = document["fixtures"]
    cases = [record["case"] for record in fixtures]
    check(cases == FIXTURE_CASES, f"fixture matrix must contain exact ordered cases: {FIXTURE_CASES}")
    paths = [record["path"] for record in fixtures]
    check(len(paths) == len(set(paths)), "fixture matrix contains duplicate paths")
    for record in fixtures:
        member = contained_file(fixture_root, record["path"], f"fixture {record['case']}")
        check(sha256_file(member) == record["sha256"], f"fixture digest drift: {record['case']}")
        check(record["platform_result"] == "not-run", f"fixture makes a platform claim: {record['case']}")
    repository_files = exact_files(fixture_root / "repositories")
    expected_files = {
        PurePosixPath(path).relative_to("repositories").as_posix() for path in paths
    }
    check(repository_files == expected_files, "fixture inventory does not bind the exact repository-shape tree")
    support = document["fixture_support"]
    check(
        support
        == [
            {
                "path": ".gitattributes",
                "sha256": "1edeaa40ea3e099263a3767e448ef00beb7d4c0e02156682177cd8310fefebe7",
            }
        ],
        "fixture support inventory changed",
    )
    support_member = contained_file(
        fixture_root, support[0]["path"], "fixture support"
    )
    check(
        sha256_file(support_member) == support[0]["sha256"],
        "fixture support digest drift",
    )
    check(
        document["candidate"]["fixture_revision"]
        == canonical_sha256(
            {"fixtures": fixtures, "fixture_support": support}
        ),
        "candidate fixture revision does not bind the exact fixture matrix",
    )


def validate_artifacts(document: dict[str, Any], fixture_root: Path) -> None:
    artifacts = document["artifacts"]
    platforms = [record["platform"] for record in artifacts]
    check(platforms == list(PLATFORMS), f"artifact matrix must contain exact ordered platforms: {list(PLATFORMS)}")
    check(len(platforms) == len(set(platforms)), "artifact matrix contains duplicate platforms")
    named_paths: list[str] = []
    for record in artifacts:
        expected_target, expected_runner = PLATFORMS[record["platform"]]
        check(record["target"] == expected_target, f"target drift: {record['platform']}")
        check(record["runner"] == expected_runner, f"runner drift: {record['platform']}")
        check(record["candidate"] == document["candidate"], f"candidate identity drift: {record['platform']}")
        named_paths.extend([record["artifact"], record["checksum"]])
        artifact = contained_file(fixture_root, record["artifact"], f"artifact {record['platform']}")
        checksum = contained_file(fixture_root, record["checksum"], f"checksum {record['platform']}")
        actual_artifact_sha = sha256_file(artifact)
        check(actual_artifact_sha == record["artifact_sha256"], f"artifact digest drift: {record['platform']}")
        check(sha256_file(checksum) == record["checksum_sha256"], f"checksum file digest drift: {record['platform']}")
        expected_checksum = f"{actual_artifact_sha}  {artifact.name}\n".encode("ascii")
        try:
            checksum_bytes = checksum.read_bytes()
        except OSError as error:
            raise VerificationError(f"cannot read checksum file: {checksum}") from error
        check(checksum_bytes == expected_checksum, f"checksum content drift: {record['platform']}")
    check(len(named_paths) == len(set(named_paths)), "artifact/checksum path collision")
    artifact_files = exact_files(fixture_root / "artifacts")
    expected_artifact_files = {
        PurePosixPath(path).relative_to("artifacts").as_posix() for path in named_paths
    }
    check(artifact_files == expected_artifact_files, "artifact inventory does not bind the exact artifact/checksum tree")

    expected_all_files = {
        "phase7-release-proof.json",
        *[record["path"] for record in document["fixtures"]],
        *[record["path"] for record in document["fixture_support"]],
        *named_paths,
    }
    check(
        exact_files(fixture_root) == expected_all_files,
        "Phase 7 evidence does not bind the exact fixture root",
    )


def validate_fixture_only_state(document: dict[str, Any]) -> None:
    if document["evidence_kind"] != "fixture-only-non-production":
        return
    candidate = document["candidate"]
    check(
        candidate["source_revision"] == FIXTURE_SOURCE_REVISION,
        "fixture source revision drift",
    )
    check(
        candidate["workflow_revision"] == FIXTURE_SOURCE_REVISION,
        "fixture workflow revision drift",
    )
    for field, path in FIXTURE_IDENTITY_BINDINGS.items():
        check(sha256_file(path) == candidate[field], f"fixture candidate identity binding drift: {field}")
    for record in document["artifacts"]:
        check(record["authentication"]["state"] == "pending", f"fixture claims authentication: {record['platform']}")
        for field in ("build_result", "direct_binary_result", "installer_result"):
            check(record[field]["state"] == "pending", f"fixture claims {field}: {record['platform']}")
            check(record[field]["evidence"] == [], f"pending fixture result carries evidence: {record['platform']}")
        check(record["authentication"]["evidence"] == [], f"pending fixture authentication carries evidence: {record['platform']}")


def validate_closed_promotion(document: dict[str, Any], require_promotable: bool) -> None:
    state = document["promotion"]
    check(state["blockers"] == BLOCKERS, "promotion blocker set changed")
    check(state["phase6_live_evidence"] == "pending", "deferred Phase 6 evidence is no longer pending")
    check(state["phase7_results"] == "pending", "Phase 7 results are no longer pending")
    check(state["phase7_acceptance"] == "blocked", "Phase 7 acceptance is not blocked")
    check(state["phase8"] == "closed", "Phase 8 is not closed")
    for field in (
        "production",
        "promotable",
        "tag_authorized",
        "publish_authorized",
        "promotion_authorized",
        "production_signing_authorized",
    ):
        check(state[field] is False, f"unsafe release claim: {field}")
    if require_promotable:
        raise PendingPromotion(
            "deferred Phase 6 live evidence and all five Phase 7 platform results are pending; "
            "fixture-only evidence cannot authorize acceptance, tag, publish, signing, or promotion"
        )


def verify(evidence_path: Path, schema_path: Path, fixture_root: Path, require_promotable: bool) -> None:
    contract = load_json(schema_path)
    check(isinstance(contract, dict), "schema is not an object")
    check(contract.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "schema is not Draft 2020-12")
    assert_closed_schema(contract)
    document = load_json(evidence_path)
    check(isinstance(document, dict), "evidence is not an object")
    validate_schema(document, contract, contract, "phase7 proof")
    validate_fixture_matrix(document, fixture_root)
    validate_artifacts(document, fixture_root)
    validate_fixture_only_state(document)
    validate_closed_promotion(document, require_promotable)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--require-promotable", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        verify(
            arguments.evidence,
            arguments.schema,
            arguments.fixture_root,
            arguments.require_promotable,
        )
    except PendingPromotion as error:
        print(f"Phase 7 promotion blocked: {error}", file=sys.stderr)
        return 2
    except VerificationError as error:
        print(f"Phase 7 release proof verification failed: {error}", file=sys.stderr)
        return 1
    print(
        "Phase 7 fixture/candidate contract passed; no platform passed and acceptance, tag, "
        "publish, signing, promotion, and Phase 8 remain blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

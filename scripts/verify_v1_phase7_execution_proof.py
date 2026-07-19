#!/usr/bin/env python3
"""Verify one or the exact five Phase 7 execution-proof receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


PLATFORMS = ["macos-arm64", "macos-x64", "linux-x64", "linux-arm64", "windows-x64"]
CASES = ["fresh", "brownfield", "nested-instructions", "docs-only", "monorepo", "spaces-unicode", "lf", "crlf", "custom-update", "bridge"]
COMMANDS = ["install", "update", "audit", "scaffold", "status", "version"]
BLOCKERS = ["deferred-phase6-live-p0-p7-evidence-pending", "remote-five-platform-execution-pending", "artifact-provenance-attestation-pending", "platform-acceptance-pending"]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}$")


class VerificationError(Exception):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        check(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def keys(document: dict[str, object], expected: set[str], label: str) -> None:
    check(set(document) == expected, f"{label} fields are not closed")


def load(path: Path) -> dict[str, object]:
    check(path.is_file() and not path.is_symlink(), f"proof is missing or unsafe: {path}")
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=strict_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"proof is invalid JSON: {path}") from error
    check(isinstance(value, dict), "proof root is not an object")
    return value


def verify(document: dict[str, object]) -> None:
    keys(document, {"schema", "evidence_kind", "candidate", "execution_workflow", "environment", "artifact", "commands", "fixtures", "normalized_contract_sha256", "authority"}, "proof")
    check(document["schema"] == "repository-harness-v1-phase7-execution-proof/v1", "proof schema identity changed")
    check(document["evidence_kind"] == "local-or-runner-test-fixture-non-production", "proof makes a production claim")
    candidate = document["candidate"]
    check(isinstance(candidate, dict), "candidate identity is missing")
    keys(candidate, {"source_commit", "source_tree", "cargo_lock_sha256", "command_binding_sha256"}, "candidate")
    check(REVISION.fullmatch(candidate["source_commit"]) is not None and REVISION.fullmatch(candidate["source_tree"]) is not None, "candidate Git identity is invalid")
    check(SHA256.fullmatch(candidate["cargo_lock_sha256"]) is not None and SHA256.fullmatch(candidate["command_binding_sha256"]) is not None, "candidate input identity is invalid")
    workflow = document["execution_workflow"]
    check(isinstance(workflow, dict), "workflow identity is missing")
    keys(workflow, {"path", "revision", "sha256"}, "workflow")
    check(workflow["path"] == ".github/workflows/harness-v1-release.yml" and REVISION.fullmatch(workflow["revision"]) is not None and SHA256.fullmatch(workflow["sha256"]) is not None, "workflow identity is invalid")
    environment = document["environment"]
    check(isinstance(environment, dict), "environment is missing")
    keys(environment, {"platform", "installer"}, "environment")
    check(environment["platform"] in PLATFORMS, "platform is unsupported")
    expected_installer = "powershell" if environment["platform"] == "windows-x64" else "bash"
    check(environment["installer"] == expected_installer, "platform installer is wrong")
    artifact = document["artifact"]
    check(isinstance(artifact, dict), "artifact is missing")
    keys(artifact, {"sha256", "authentication", "provenance"}, "artifact")
    check(SHA256.fullmatch(artifact["sha256"]) is not None, "artifact digest is invalid")
    check(artifact["authentication"] == "checksum-verified-before-every-execution", "artifact did not authenticate before execution")
    check(artifact["provenance"] == "unattested-not-authenticated", "proof overclaims provenance")
    check(document["commands"] == COMMANDS, "six-command core changed")
    fixtures = document["fixtures"]
    check(isinstance(fixtures, list) and [item.get("case") for item in fixtures if isinstance(item, dict)] == CASES, "fixture matrix is incomplete or reordered")
    expected_fixture_fields = {"case", "owner_bytes_preserved", "language_manifests_ignored", "line_endings_preserved", "install", "update", "audit", "scaffold", "status", "version", "recovery_refusal", "normalized_sha256"}
    expected_values = {
        "owner_bytes_preserved": True,
        "language_manifests_ignored": True,
        "line_endings_preserved": True,
        "install": "committed-authenticated-test-payload",
        "update": "idempotent-authenticated-test-payload",
        "audit": "ready-no-target-execution",
        "scaffold": "committed-one-neutral-artifact",
        "status": "ready",
        "version": "success",
        "recovery_refusal": "missing-operation-failed-closed-before-mutation",
    }
    for fixture in fixtures:
        keys(fixture, expected_fixture_fields, f"fixture {fixture.get('case')}")
        check(all(fixture[field] == value for field, value in expected_values.items()), f"fixture {fixture['case']} result changed")
        check(SHA256.fullmatch(fixture["normalized_sha256"]) is not None, f"fixture {fixture['case']} normalized digest is invalid")
    expected_contract = sha(canonical([fixture["normalized_sha256"] for fixture in fixtures]))
    check(document["normalized_contract_sha256"] == expected_contract, "normalized contract digest drifted")
    authority = document["authority"]
    check(isinstance(authority, dict), "authority state is missing")
    keys(authority, {"phase6_live_evidence", "platform_accepted", "phase7_accepted", "promotable", "production", "phase8", "blockers"}, "authority")
    check(authority == {"phase6_live_evidence": "pending", "platform_accepted": False, "phase7_accepted": False, "promotable": False, "production": False, "phase8": "closed", "blockers": BLOCKERS}, "proof opened a blocked authority")


def verify_collection(documents: list[dict[str, object]], require_five: bool) -> None:
    for document in documents:
        verify(document)
    if require_five:
        check(len(documents) == 5, "exactly five proofs are required")
        check([document["environment"]["platform"] for document in documents] == PLATFORMS, "five-platform proof order or inventory changed")
        for field in ("candidate", "execution_workflow", "commands", "normalized_contract_sha256"):
            check(all(document[field] == documents[0][field] for document in documents), f"cross-platform {field} equivalence failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("proofs", nargs="+")
    parser.add_argument("--require-five", action="store_true")
    arguments = parser.parse_args()
    try:
        documents = [load(Path(path)) for path in arguments.proofs]
        verify_collection(documents, arguments.require_five)
        print(f"Verified {len(documents)} non-production Phase 7 execution proof(s); platform acceptance remains blocked")
        return 0
    except VerificationError as error:
        print(f"Phase 7 execution proof verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

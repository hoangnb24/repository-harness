#!/usr/bin/env python3
"""Verify one or the exact five Phase 7 execution-proof receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from v1_build_receipt_common import PLATFORMS as BUILD_PLATFORMS, ReceiptError
from verify_v1_build_receipts import verify_artifact_identity_collection

PLATFORMS = list(BUILD_PLATFORMS)
CASES = ["fresh", "brownfield", "nested-instructions", "docs-only", "monorepo", "spaces-unicode", "lf", "crlf", "custom-update", "bridge"]
COMMANDS = ["install", "update", "audit", "scaffold", "status", "version"]
BLOCKERS = ["deferred-phase6-live-p0-p7-evidence-pending", "five-platform-semantic-equivalence-pending", "safe-windows-repository-mutation-pending", "platform-acceptance-pending", "phase7-acceptance-pending", "production-release-signing-and-promotion-blocked"]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}$")
WORKFLOW_PATH = ".github/workflows/harness-v1-release.yml"
WINDOWS_REFUSAL_TEST_SHA256 = (
    "23c2b91db380bef9528b72f7519f6f7c7ac021185a5bdddc97e46bf0685e4fb9"
)


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


def verify_windows_refusal_test(payload: bytes) -> None:
    check(
        sha(payload) == WINDOWS_REFUSAL_TEST_SHA256,
        "Windows refusal test bytes differ from the reviewed PowerShell 5.1 contract",
    )


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


def git_bytes(repository: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    check(result.returncode == 0, f"git {' '.join(arguments)} failed for expected identity")
    return result.stdout


def expected_identity(repository: Path, candidate: str, workflow_revision: str) -> dict[str, object]:
    check(repository.is_absolute() and repository.is_dir() and not repository.is_symlink(), "repository root is unavailable or unsafe")
    check(REVISION.fullmatch(candidate) is not None, "expected candidate is not exact 40-hex")
    check(REVISION.fullmatch(workflow_revision) is not None, "expected workflow revision is not exact 40-hex")
    check(candidate == workflow_revision, "expected candidate and workflow revision must be identical")
    resolved_candidate = git_bytes(repository, "rev-parse", "--verify", f"{candidate}^{{commit}}").decode("ascii").strip()
    resolved_workflow = git_bytes(repository, "rev-parse", "--verify", f"{workflow_revision}^{{commit}}").decode("ascii").strip()
    check(resolved_candidate == candidate, "expected candidate did not resolve exactly")
    check(resolved_workflow == workflow_revision, "expected workflow revision did not resolve exactly")
    candidate_identity = {
        "source_commit": candidate,
        "source_tree": git_bytes(repository, "rev-parse", f"{candidate}^{{tree}}").decode("ascii").strip(),
        "cargo_lock_sha256": sha(git_bytes(repository, "show", f"{candidate}:Cargo.lock")),
        "command_binding_sha256": sha(git_bytes(repository, "show", f"{candidate}:release/contracts/v1/command-implementation-binding.json")),
    }
    workflow_identity = {
        "path": WORKFLOW_PATH,
        "revision": workflow_revision,
        "sha256": sha(git_bytes(repository, "show", f"{workflow_revision}:{WORKFLOW_PATH}")),
    }
    return {"candidate": candidate_identity, "execution_workflow": workflow_identity}


def verify_normalized_command(value: object, label: str) -> None:
    check(isinstance(value, dict), f"{label} normalized command is missing")
    keys(value, {"command", "outcome", "exit_code", "mutation", "repository_mode", "release_role", "release_sequence", "release_index_sha256", "readiness", "violation_codes", "notice_codes"}, label)
    check(isinstance(value["command"], str) and value["command"], f"{label} command is invalid")
    check(isinstance(value["outcome"], str) and value["outcome"], f"{label} outcome is invalid")
    check(isinstance(value["exit_code"], int), f"{label} exit code is invalid")
    check(isinstance(value["mutation"], str) and value["mutation"], f"{label} mutation is invalid")
    for field in ("repository_mode", "release_role", "readiness"):
        check(value[field] is None or isinstance(value[field], str), f"{label} {field} is invalid")
    check(value["release_sequence"] is None or isinstance(value["release_sequence"], int), f"{label} release sequence is invalid")
    check(value["release_index_sha256"] is None or SHA256.fullmatch(value["release_index_sha256"]) is not None, f"{label} release digest is invalid")
    for field in ("violation_codes", "notice_codes"):
        check(isinstance(value[field], list) and all(isinstance(item, str) for item in value[field]), f"{label} {field} is invalid")


def verify_normalized_result(value: object, mode: str, label: str) -> None:
    check(isinstance(value, dict), f"{label} normalized result is missing")
    keys(value, {"mode", "commands", "recovery_refusal"}, label)
    check(value["mode"] == mode, f"{label} normalized mode changed")
    commands = value["commands"]
    check(isinstance(commands, list) and len(commands) == 6, f"{label} normalized command inventory changed")
    for index, command in enumerate(commands):
        verify_normalized_command(command, f"{label} command {index}")
    check([command["command"] for command in commands] == COMMANDS, f"{label} normalized command order changed")
    recovery = value["recovery_refusal"]
    verify_normalized_command(recovery, f"{label} recovery")
    check(recovery["command"] == "update" and recovery["mutation"] == "none", f"{label} recovery refusal changed")
    if mode == "full-native-test-fixture":
        check([command["exit_code"] for command in commands] == [0, 0, 0, 0, 0, 0], f"{label} native command exits changed")
        check([command["mutation"] for command in commands] == ["committed", "none", "none", "committed", "none", "none"], f"{label} native mutations changed")
        check(recovery["exit_code"] == 3, f"{label} native recovery refusal exit changed")
    else:
        check(mode == "controlled-unsupported-before-mutation", f"{label} execution mode is unsupported")
        check([command["exit_code"] for command in commands] == [74, 74, 74, 74, 74, 0], f"{label} Windows controlled-unsupported exits changed")
        check(all(command["mutation"] == "none" for command in commands), f"{label} Windows command crossed mutation boundary")
        check(recovery["exit_code"] == 74, f"{label} Windows recovery refusal exit changed")


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
    check(workflow["path"] == WORKFLOW_PATH and REVISION.fullmatch(workflow["revision"]) is not None and SHA256.fullmatch(workflow["sha256"]) is not None, "workflow identity is invalid")
    check(candidate["source_commit"] == workflow["revision"], "receipt candidate and workflow revision differ")
    environment = document["environment"]
    check(isinstance(environment, dict), "environment is missing")
    keys(environment, {"platform", "installer", "behavior"}, "environment")
    check(environment["platform"] in PLATFORMS, "platform is unsupported")
    expected_installer = (
        "powershell-controlled-unsupported-before-mutation"
        if environment["platform"] == "windows-x64"
        else "bash"
    )
    check(environment["installer"] == expected_installer, "platform installer is wrong")
    expected_behavior = "controlled-unsupported-before-mutation" if environment["platform"] == "windows-x64" else "full-native-test-fixture"
    check(environment["behavior"] == expected_behavior, "platform behavior claim is wrong")
    artifact = document["artifact"]
    check(isinstance(artifact, dict), "artifact is missing")
    keys(artifact, {"platform", "target", "runner", "name", "sha256", "authentication", "provenance", "attestation_bundle_sha256", "provenance_verification_sha256"}, "artifact")
    platform_name = environment["platform"]
    target, runner, artifact_name = BUILD_PLATFORMS[platform_name]
    check(
        {
            "platform": artifact["platform"],
            "target": artifact["target"],
            "runner": artifact["runner"],
            "name": artifact["name"],
        }
        == {
            "platform": platform_name,
            "target": target,
            "runner": runner,
            "name": artifact_name,
        },
        "artifact platform/target/runner/name tuple is invalid",
    )
    check(SHA256.fullmatch(artifact["sha256"]) is not None, "artifact digest is invalid")
    check(artifact["authentication"] == "checksum-and-github-sigstore-verified-before-every-execution", "artifact did not authenticate before execution")
    check(artifact["provenance"] == "github-sigstore-attested", "proof lacks verified GitHub/Sigstore provenance")
    check(SHA256.fullmatch(artifact["attestation_bundle_sha256"]) is not None, "attestation bundle digest is invalid")
    check(SHA256.fullmatch(artifact["provenance_verification_sha256"]) is not None, "provenance verification digest is invalid")
    check(document["commands"] == COMMANDS, "six-command core changed")
    fixtures = document["fixtures"]
    check(isinstance(fixtures, list) and [item.get("case") for item in fixtures if isinstance(item, dict)] == CASES, "fixture matrix is incomplete or reordered")
    expected_fixture_fields = {"case", "execution_status", "owner_bytes_preserved", "language_manifests_ignored", "line_endings_preserved", "normalized_result", "normalized_sha256"}
    expected_values = {
        "execution_status": expected_behavior,
        "owner_bytes_preserved": True,
        "language_manifests_ignored": True,
        "line_endings_preserved": True,
    }
    for fixture in fixtures:
        keys(fixture, expected_fixture_fields, f"fixture {fixture.get('case')}")
        check(all(fixture[field] == value for field, value in expected_values.items()), f"fixture {fixture['case']} result changed")
        verify_normalized_result(fixture["normalized_result"], expected_behavior, f"fixture {fixture['case']}")
        check(SHA256.fullmatch(fixture["normalized_sha256"]) is not None, f"fixture {fixture['case']} normalized digest is invalid")
        check(fixture["normalized_sha256"] == sha(canonical(fixture["normalized_result"])), f"fixture {fixture['case']} normalized payload digest drifted")
    expected_contract = sha(canonical([
        {"case": fixture["case"], "normalized_result": fixture["normalized_result"]}
        for fixture in fixtures
    ]))
    check(document["normalized_contract_sha256"] == expected_contract, "normalized contract digest drifted")
    authority = document["authority"]
    check(isinstance(authority, dict), "authority state is missing")
    keys(authority, {"phase6_live_evidence", "five_platform_equivalence", "platform_accepted", "phase7_accepted", "promotable", "production", "phase8", "blockers"}, "authority")
    check(authority == {"phase6_live_evidence": "pending", "five_platform_equivalence": "pending", "platform_accepted": False, "phase7_accepted": False, "promotable": False, "production": False, "phase8": "closed", "blockers": BLOCKERS}, "proof opened a blocked authority")


def verify_collection(
    documents: list[dict[str, object]],
    require_five: bool,
    expected: dict[str, object] | None = None,
    expected_artifacts: dict[str, dict[str, str]] | None = None,
) -> None:
    for document in documents:
        verify(document)
    if require_five:
        check(expected is not None, "exact-five verification requires independent candidate and workflow identity")
        check(expected_artifacts is not None, "exact-five verification requires independently verified build artifacts")
        check(len(documents) == 5, "exactly five proofs are required")
        check([document["environment"]["platform"] for document in documents] == PLATFORMS, "five-platform proof order or inventory changed")
        check(set(expected_artifacts) == set(PLATFORMS), "verified build artifact inventory is not exact-five")
        for document in documents:
            check(document["candidate"] == expected["candidate"], "receipt candidate does not match the independently resolved candidate")
            check(document["execution_workflow"] == expected["execution_workflow"], "receipt workflow does not match independently resolved workflow bytes")
            platform_name = document["environment"]["platform"]
            artifact = document["artifact"]
            bound_artifact = {
                field: artifact[field]
                for field in ("platform", "target", "runner", "name", "sha256", "attestation_bundle_sha256", "provenance_verification_sha256")
            }
            check(
                bound_artifact == expected_artifacts[platform_name],
                f"execution proof artifact identity does not match verified build receipt: {platform_name}",
            )
        check(all(document["commands"] == documents[0]["commands"] for document in documents), "cross-platform command identity failed")
        check(all(document["normalized_contract_sha256"] == documents[0]["normalized_contract_sha256"] for document in documents[:4]), "Unix normalized equivalence failed")
        check(documents[-1]["authority"]["five_platform_equivalence"] == "pending", "Windows receipt overclaimed five-platform equivalence")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("proofs", nargs="+")
    parser.add_argument("--require-five", action="store_true")
    parser.add_argument("--candidate")
    parser.add_argument("--workflow-revision")
    parser.add_argument("--repository-root")
    parser.add_argument("--build-receipt-root")
    arguments = parser.parse_args()
    try:
        documents = [load(Path(path)) for path in arguments.proofs]
        expected = None
        if arguments.require_five:
            check(
                arguments.candidate is not None
                and arguments.workflow_revision is not None
                and arguments.repository_root is not None,
                "--require-five requires --candidate, --workflow-revision, --repository-root, and --build-receipt-root",
            )
            check(arguments.build_receipt_root is not None, "--require-five requires --build-receipt-root")
            expected = expected_identity(
                Path(arguments.repository_root), arguments.candidate, arguments.workflow_revision
            )
            try:
                expected_artifacts = verify_artifact_identity_collection(
                    Path(arguments.build_receipt_root),
                    arguments.candidate,
                    arguments.workflow_revision,
                    True,
                )
            except ReceiptError as error:
                raise VerificationError(f"build receipt collection failed independent verification: {error}") from error
        else:
            expected_artifacts = None
        verify_collection(documents, arguments.require_five, expected, expected_artifacts)
        suffix = "; five-platform equivalence remains pending" if arguments.require_five else ""
        print(f"Verified {len(documents)} non-production Phase 7 execution proof(s){suffix}; platform acceptance remains blocked")
        return 0
    except VerificationError as error:
        print(f"Phase 7 execution proof verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

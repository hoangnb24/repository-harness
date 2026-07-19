#!/usr/bin/env python3
"""Static fail-closed policy for the unpromoted Phase 7 attestation workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/harness-v1-release.yml"
ATTEST_ACTION = "actions/attest-build-provenance@96278af6caaf10aea03fd8d33a09a777ca52d62f"
PRIVILEGED_DOWNLOAD_ACTION = "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"
PRIVILEGED_UPLOAD_ACTION = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"


class WorkflowPolicyError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowPolicyError(message)


def job_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n.*?(?=^  [a-zA-Z0-9_-]+:\n|\Z)",
        text,
    )
    require(match is not None, f"workflow job is missing: {name}")
    return match.group(0)


def require_permissions(block: str, expected: str, label: str) -> None:
    match = re.search(r"(?m)^    permissions:\n((?:      [^\n]+\n)+)", block)
    require(
        match is not None and match.group(1) == expected,
        f"{label} permissions are not exact",
    )
    require(block.count("permissions:") == 1, f"{label} has ambiguous permission blocks")


def verify_text(text: str) -> None:
    require(
        text.count("  PYTHONDONTWRITEBYTECODE: '1'") == 1,
        "workflow must disable repository bytecode generation globally",
    )
    require(text.count(ATTEST_ACTION) == 1, "attestation action must use the verified exact v3 commit once")
    require("actions/attest-build-provenance@v3" not in text, "attestation action uses a mutable tag")
    require(text.count("id-token: write") == 1, "OIDC permission must exist only on the attestation job")
    require(text.count("attestations: write") == 1, "attestation write permission must exist only on the attestation job")
    require("contents: write" not in text and "packages: write" not in text and "actions: write" not in text, "workflow grants excess write permission")
    require("secrets." not in text and "BEGIN PRIVATE KEY" not in text and "COSIGN_PRIVATE_KEY" not in text, "workflow uses a repository secret or private key")
    require("production: true" not in text and "promotable: true" not in text, "workflow overclaims production or promotion authority")

    build = job_block(text, "build-native-artifact")
    attest = job_block(text, "attest-native-artifact")
    execute = job_block(text, "verify-execute-native-proof")
    collect = job_block(text, "collect-receipts")
    read_only = "      contents: read\n"
    require_permissions(build, read_only, "native build job")
    require_permissions(
        attest,
        "      contents: read\n      id-token: write\n      attestations: write\n",
        "attestation job",
    )
    require_permissions(execute, read_only, "verify/execute job")
    require_permissions(collect, read_only, "collector job")
    require(
        text.index("  build-native-artifact:")
        < text.index("  attest-native-artifact:")
        < text.index("  verify-execute-native-proof:")
        < text.index("  collect-receipts:"),
        "build, attestation, verification/execution, and collection jobs are reordered",
    )
    require("needs: [repository-identity, resolve-candidate, build-native-artifact]" in attest, "attestation does not depend on the completed build")
    require("needs: [repository-identity, resolve-candidate, attest-native-artifact]" in execute, "execution does not depend on completed attestation")
    require("needs: [resolve-candidate, verify-execute-native-proof]" in collect, "collection does not depend on verified execution")
    require(ATTEST_ACTION not in build and ATTEST_ACTION in attest and ATTEST_ACTION not in execute, "attestation action escaped its isolated job")
    privileged_actions = re.findall(r"(?m)^        uses: ([^\s#]+)", attest)
    require(
        privileged_actions
        == [PRIVILEGED_DOWNLOAD_ACTION, ATTEST_ACTION, PRIVILEGED_UPLOAD_ACTION],
        "privileged attestation job actions are not the exact verified commits",
    )
    require(
        "actions/download-artifact@v" not in attest
        and "actions/upload-artifact@v" not in attest,
        "privileged attestation job uses a mutable artifact action",
    )
    require("scripts/finalize_v1_build_receipt.py" not in attest and "scripts/run_v1_phase7_execution_proof.py" not in attest, "attestation job can execute candidate code")
    require("subject-path: ${{ runner.temp }}/harness-v1-attestation-input-${{ matrix.platform }}/${{ matrix.artifact }}" in attest, "attestation subject is not the exact downloaded native artifact")
    require("ATTESTATION_BUNDLE: ${{ steps.attest-native-artifact.outputs.bundle-path }}" in attest, "signed bundle output is not retained")
    for artifact_name in ("harness-v1-native-artifact-${{ matrix.platform }}", "harness-v1-attestation-${{ matrix.platform }}"):
        require(artifact_name in attest and artifact_name in execute, f"exact artifact handoff is incomplete: {artifact_name}")

    python_path = '"${{ steps.python.outputs.python-path }}"'
    for script in (
        "scripts/finalize_v1_build_receipt.py",
        "scripts/run_v1_phase7_execution_proof.py",
        "scripts/verify_v1_build_receipts.py",
    ):
        require(f"{python_path} {script}" in execute, f"verify/execute job does not use setup-python output for {script}")
    require(f"{python_path} scripts/verify_v1_build_receipts.py" in collect, "collector receipt verifier does not use setup-python output")
    require(f"{python_path} scripts/verify_v1_phase7_execution_proof.py" in collect, "collector execution verifier does not use setup-python output")
    require("python3 " not in execute and "python3 " not in collect, "workflow bypasses the setup-python output")
    order = [
        execute.find("scripts/finalize_v1_build_receipt.py"),
        execute.find("scripts/run_v1_phase7_execution_proof.py"),
        execute.find("scripts/verify_v1_build_receipts.py"),
        execute.find("tests/release/test-install-harness-v1-windows-unsupported.ps1"),
    ]
    require(all(index >= 0 for index in order), "verification or execution step is missing")
    require(order == sorted(order) and len(set(order)) == len(order), "signed-bundle verification occurs after candidate execution")
    require("--build-receipt-directory \"$RECEIPT_OUTPUT\"" in execute, "execution runner cannot repeat signed-bundle verification")

    require(text.startswith("name: Repository Harness V1 Proof (Unpromoted)"), "workflow lost its unpromoted identity")
    require("refs/heads/refactor/harness-v1" in text and "workflow_dispatch:" not in text, "workflow widened its sentinel push authority")
    for prohibited in (
        "gh release", "git tag", "git push", "cargo publish", "npm publish",
        "softprops/action-gh-release", "ncipollo/release-action", "gpg --sign",
    ):
        require(prohibited not in text, f"workflow contains prohibited release authority: {prohibited}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", nargs="?", type=Path, default=WORKFLOW)
    arguments = parser.parse_args()
    try:
        verify_text(arguments.workflow.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, WorkflowPolicyError) as error:
        print(f"Phase 7 attestation workflow verification failed: {error}", file=sys.stderr)
        return 1
    print("Phase 7 attestation workflow is exact-pinned, least-privilege, pre-execution, and non-promotable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

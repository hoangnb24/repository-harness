#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
cd "$root"

python3 scripts/verify_v1_attestation_workflow.py
python3 - <<'PY'
from pathlib import Path
import sys

root = Path.cwd()
sys.path.insert(0, str(root / "scripts"))
from verify_v1_attestation_workflow import (
    ATTEST_ACTION,
    PRIVILEGED_DOWNLOAD_ACTION,
    PRIVILEGED_UPLOAD_ACTION,
    WorkflowPolicyError,
    verify_text,
)

workflow = (root / ".github/workflows/harness-v1-release.yml").read_text(encoding="utf-8")

def rejected(name, changed):
    try:
        verify_text(changed)
    except WorkflowPolicyError:
        print(f"ok - rejected {name}")
    else:
        raise AssertionError(f"accepted {name}")

rejected("unpinned attestation action", workflow.replace(ATTEST_ACTION, "actions/attest-build-provenance@v3"))
rejected("bytecode defense disabled", workflow.replace("  PYTHONDONTWRITEBYTECODE: '1'", "  PYTHONDONTWRITEBYTECODE: '0'"))
rejected("mutable privileged download action", workflow.replace(PRIVILEGED_DOWNLOAD_ACTION, "actions/download-artifact@v8"))
rejected("substituted privileged download action", workflow.replace(PRIVILEGED_DOWNLOAD_ACTION, "attacker/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"))
rejected("wrong privileged download commit", workflow.replace(PRIVILEGED_DOWNLOAD_ACTION, "actions/download-artifact@" + "0" * 40))
rejected("mutable privileged upload action", workflow.replace(PRIVILEGED_UPLOAD_ACTION, "actions/upload-artifact@v7"))
rejected("substituted privileged upload action", workflow.replace(PRIVILEGED_UPLOAD_ACTION, "attacker/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"))
rejected("wrong privileged upload commit", workflow.replace(PRIVILEGED_UPLOAD_ACTION, "actions/upload-artifact@" + "0" * 40))
rejected("excess permission", workflow.replace("      attestations: write\n", "      attestations: write\n      packages: write\n", 1))
rejected("OIDC permission on build job", workflow.replace("  build-native-artifact:\n", "  build-native-artifact:\n# id-token: write\n", 1))
rejected(
    "OIDC permission moved to execution job",
    workflow.replace("      id-token: write\n", "", 1).replace(
        "  verify-execute-native-proof:\n",
        "  verify-execute-native-proof:\n    # id-token: write\n",
        1,
    ),
)
rejected("repository secret use", workflow + "\n# ${{ secrets.SIGNING_KEY }}\n")
rejected("missing attestation generation", workflow.replace(f"        uses: {ATTEST_ACTION} # v3.2.0\n", ""))
rejected("authority overclaim", workflow + "\n# production: true\n")
rejected(
    "attestation job candidate execution",
    workflow.replace(
        "\n  verify-execute-native-proof:\n",
        "\n      - run: scripts/run_v1_phase7_execution_proof.py\n\n  verify-execute-native-proof:\n",
        1,
    ),
)
rejected(
    "broken build to attestation dependency",
    workflow.replace(
        "needs: [repository-identity, resolve-candidate, build-native-artifact]",
        "needs: [repository-identity, resolve-candidate]",
        1,
    ),
)
rejected(
    "system python finalizer",
    workflow.replace(
        '"${{ steps.python.outputs.python-path }}" scripts/finalize_v1_build_receipt.py',
        "python3 scripts/finalize_v1_build_receipt.py",
        1,
    ),
)
rejected(
    "shebang execution proof",
    workflow.replace(
        '"${{ steps.python.outputs.python-path }}" scripts/run_v1_phase7_execution_proof.py',
        "scripts/run_v1_phase7_execution_proof.py",
        1,
    ),
)
rejected(
    "substituted attestation handoff",
    workflow.replace("harness-v1-attestation-${{ matrix.platform }}", "substituted-attestation"),
)

execution = "scripts/run_v1_phase7_execution_proof.py"
verification = "scripts/finalize_v1_build_receipt.py"
reordered = workflow.replace(execution, "EXECUTION_PLACEHOLDER", 1)
reordered = reordered.replace(verification, execution, 1).replace("EXECUTION_PLACEHOLDER", verification, 1)
rejected("verification after execution", reordered)
PY

echo "Phase 7 attestation workflow adversaries passed"

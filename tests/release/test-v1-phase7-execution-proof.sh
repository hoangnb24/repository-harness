#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
cd "$root"

starting_status=$(git status --short --untracked-files=all)
cargo build -p harness-core --bin harness
python3 - <<'PY'
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


root = Path.cwd()


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


runner = module("phase7_execution_runner", root / "scripts/run_v1_phase7_execution_proof.py")
verifier = module("phase7_execution_verifier", root / "scripts/verify_v1_phase7_execution_proof.py")
platform_name = runner.native_platform()
suffix = ".exe" if platform_name == "windows-x64" else ""
built = root / f"target/debug/harness{suffix}"
assert built.is_file()

with tempfile.TemporaryDirectory(prefix="phase7-execution-focused-") as temporary_text:
    temporary = Path(temporary_text)
    artifact_name = f"harness-{platform_name}{suffix}"
    artifact = temporary / artifact_name
    shutil.copyfile(built, artifact)
    artifact.chmod(0o755)
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    checksum = temporary / f"{artifact_name}.sha256"
    checksum.write_text(f"{artifact_sha}  {artifact_name}\n", encoding="ascii")

    external = temporary / "external-input"
    prepared = subprocess.run(
        ["python3", str(root / "scripts/prepare-v1-phase7-test-release.py"), "--output", str(external)],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    assert prepared.returncode == 0, prepared.stderr.decode()

    # A tampered checksum is refused by the installer before any binary exists.
    bad_checksum = temporary / "bad.sha256"
    bad_checksum.write_text(f"{'0' * 64}  {artifact_name}\n", encoding="ascii")
    rejected = temporary / "rejected"
    rejected.mkdir()
    try:
        runner.install(artifact, bad_checksum, platform_name, rejected)
    except runner.ProofError as error:
        assert "checksum mismatch" in str(error)
    else:
        raise AssertionError("installer accepted a tampered checksum")
    assert not (rejected / "scripts/bin/harness").exists()
    assert not (rejected / "scripts/bin/harness.exe").exists()

    workspace = temporary / "cases"
    workspace.mkdir()
    records = []
    installers = set()
    for case in runner.CASES:
        record, installer = runner.run_case(
            case,
            root / "tests/fixtures/v1-phase7/repositories" / case,
            workspace,
            artifact,
            checksum,
            artifact_sha,
            platform_name,
            external / "release",
            external / "trust-state.json",
        )
        records.append(record)
        installers.add(installer)
    assert len(installers) == 1
    assert len({record["normalized_sha256"] for record in records}) == 1

    contract_sha = hashlib.sha256(runner.canonical([record["normalized_sha256"] for record in records])).hexdigest()
    document = {
        "schema": "repository-harness-v1-phase7-execution-proof/v1",
        "evidence_kind": "local-or-runner-test-fixture-non-production",
        "candidate": {
            "source_commit": "1" * 40,
            "source_tree": "2" * 40,
            "cargo_lock_sha256": "3" * 64,
            "command_binding_sha256": "4" * 64,
        },
        "execution_workflow": {
            "path": ".github/workflows/harness-v1-release.yml",
            "revision": "5" * 40,
            "sha256": "6" * 64,
        },
        "environment": {"platform": platform_name, "installer": installers.pop()},
        "artifact": {
            "sha256": artifact_sha,
            "authentication": "checksum-verified-before-every-execution",
            "provenance": "unattested-not-authenticated",
        },
        "commands": runner.COMMANDS,
        "fixtures": records,
        "normalized_contract_sha256": contract_sha,
        "authority": {
            "phase6_live_evidence": "pending",
            "platform_accepted": False,
            "phase7_accepted": False,
            "promotable": False,
            "production": False,
            "phase8": "closed",
            "blockers": runner.BLOCKERS,
        },
    }
    verifier.verify(document)
    five = []
    for platform in verifier.PLATFORMS:
        item = deepcopy(document)
        item["environment"] = {
            "platform": platform,
            "installer": "powershell" if platform == "windows-x64" else "bash",
        }
        item["artifact"]["sha256"] = hashlib.sha256(platform.encode()).hexdigest()
        five.append(item)
    verifier.verify_collection(five, True)
    drifted = deepcopy(five)
    drifted[-1]["normalized_contract_sha256"] = "0" * 64
    try:
        verifier.verify_collection(drifted, True)
    except verifier.VerificationError:
        print("ok - rejected cross-platform normalized drift")
    else:
        raise AssertionError("accepted cross-platform normalized drift")
    for name, mutate in (
        ("provenance-overclaim", lambda value: value["artifact"].update(provenance="authenticated")),
        ("platform-overclaim", lambda value: value["authority"].update(platform_accepted=True)),
        ("normalized-drift", lambda value: value.update(normalized_contract_sha256="0" * 64)),
    ):
        adversary = deepcopy(document)
        mutate(adversary)
        try:
            verifier.verify(adversary)
        except verifier.VerificationError:
            print(f"ok - rejected {name}")
        else:
            raise AssertionError(f"accepted {name}")

    schema = json.loads((root / "tests/release/schemas/phase7-execution-proof-v1.schema.json").read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False

    powershell = (root / "scripts/install-harness-v1.ps1").read_text(encoding="utf-8")
    assert powershell.index("Get-FileHash") < powershell.index("RuntimeInformation")
    assert "harness-windows-x64.exe" in powershell
    assert "unclaimed" in powershell

print("Phase 7 native execution proof covered all six commands and all ten fixtures without support claims")
PY

ending_status=$(git status --short --untracked-files=all)
if [[ "$ending_status" != "$starting_status" ]]; then
  printf 'Phase 7 execution focused test changed repository status\nbefore:\n%s\nafter:\n%s\n' \
    "$starting_status" "$ending_status" >&2
  exit 1
fi

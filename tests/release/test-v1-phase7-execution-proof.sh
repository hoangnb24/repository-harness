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
import os
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
    target_name, runner_name, artifact_name = runner.PLATFORMS[platform_name]
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
        if platform_name == "windows-x64":
            runner.windows_direct_after_installer_refusal(
                artifact, bad_checksum, platform_name, rejected
            )
        else:
            runner.install_unix(artifact, bad_checksum, platform_name, rejected)
    except runner.ProofError as error:
        assert "checksum mismatch" in str(error)
    else:
        raise AssertionError("installer accepted a tampered checksum")
    assert not (rejected / "scripts/bin/harness").exists()
    assert not (rejected / "scripts/bin/harness.exe").exists()

    # Target-controlled destination links must fail before any outside copy.
    if os.name != "nt":
        for attack in ("root-link", "scripts-link", "bin-link"):
            attack_root = temporary / f"attack-{attack}"
            outside = temporary / f"outside-{attack}"
            outside.mkdir()
            if attack == "root-link":
                os.symlink(outside, attack_root, target_is_directory=True)
            else:
                attack_root.mkdir()
                if attack == "scripts-link":
                    os.symlink(outside, attack_root / "scripts", target_is_directory=True)
                else:
                    (attack_root / "scripts").mkdir()
                    os.symlink(outside, attack_root / "scripts/bin", target_is_directory=True)
            try:
                runner.install_unix(artifact, checksum, platform_name, attack_root)
            except runner.ProofError as error:
                assert "installer failed" in str(error)
            else:
                raise AssertionError(f"installer accepted {attack}")
            assert not (outside / "harness").exists()
            assert not (outside / "harness.exe").exists()

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

    contract_sha = hashlib.sha256(runner.canonical([
        {"case": record["case"], "normalized_result": record["normalized_result"]}
        for record in records
    ])).hexdigest()
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
            "revision": "1" * 40,
            "sha256": "6" * 64,
        },
        "environment": {
            "platform": platform_name,
            "installer": installers.pop(),
            "behavior": "full-native-test-fixture",
        },
        "artifact": {
            "platform": platform_name,
            "target": target_name,
            "runner": runner_name,
            "name": artifact_name,
            "sha256": artifact_sha,
            "authentication": "checksum-and-github-sigstore-verified-before-every-execution",
            "provenance": "github-sigstore-attested",
            "attestation_bundle_sha256": "7" * 64,
            "provenance_verification_sha256": "8" * 64,
        },
        "commands": runner.COMMANDS,
        "fixtures": records,
        "normalized_contract_sha256": contract_sha,
        "authority": {
            "phase6_live_evidence": "pending",
            "five_platform_equivalence": "pending",
            "platform_accepted": False,
            "phase7_accepted": False,
            "promotable": False,
            "production": False,
            "phase8": "closed",
            "blockers": runner.BLOCKERS,
        },
    }
    verifier.verify(document)
    expected_identity = {
        "candidate": deepcopy(document["candidate"]),
        "execution_workflow": deepcopy(document["execution_workflow"]),
    }

    def closed_command(command, mode, index, *, recovery=False):
        if mode == "full-native-test-fixture":
            exit_code = 3 if recovery else 0
            mutation = "committed" if not recovery and index in (0, 3) else "none"
            outcome = "invalid" if recovery else "success"
        else:
            exit_code = 74 if recovery or index < 5 else 0
            mutation = "none"
            outcome = "controlled-unsupported" if exit_code == 74 else "success"
        return {
            "command": command,
            "outcome": outcome,
            "exit_code": exit_code,
            "mutation": mutation,
            "repository_mode": None,
            "release_role": None,
            "release_sequence": None,
            "release_index_sha256": None,
            "readiness": None,
            "violation_codes": [],
            "notice_codes": [],
        }

    def independent_fixture_document(platform):
        target, platform_runner, name = runner.PLATFORMS[platform]
        mode = (
            "controlled-unsupported-before-mutation"
            if platform == "windows-x64"
            else "full-native-test-fixture"
        )
        fixture_records = []
        for case in runner.CASES:
            normalized_result = {
                "mode": mode,
                "commands": [
                    closed_command(command, mode, index)
                    for index, command in enumerate(runner.COMMANDS)
                ],
                "recovery_refusal": closed_command("update", mode, 0, recovery=True),
            }
            fixture_records.append({
                "case": case,
                "execution_status": mode,
                "owner_bytes_preserved": True,
                "language_manifests_ignored": True,
                "line_endings_preserved": True,
                "normalized_result": normalized_result,
                "normalized_sha256": hashlib.sha256(runner.canonical(normalized_result)).hexdigest(),
            })
        artifact_identity = {
            "platform": platform,
            "target": target,
            "runner": platform_runner,
            "name": name,
            "sha256": hashlib.sha256(f"independent-build:{platform}".encode()).hexdigest(),
            "attestation_bundle_sha256": hashlib.sha256(f"independent-bundle:{platform}".encode()).hexdigest(),
            "provenance_verification_sha256": hashlib.sha256(f"independent-verification:{platform}".encode()).hexdigest(),
        }
        return {
            "schema": "repository-harness-v1-phase7-execution-proof/v1",
            "evidence_kind": "local-or-runner-test-fixture-non-production",
            "candidate": deepcopy(expected_identity["candidate"]),
            "execution_workflow": deepcopy(expected_identity["execution_workflow"]),
            "environment": {
                "platform": platform,
                "installer": (
                    "powershell-controlled-unsupported-before-mutation"
                    if platform == "windows-x64" else "bash"
                ),
                "behavior": mode,
            },
            "artifact": {
                **artifact_identity,
                "authentication": "checksum-and-github-sigstore-verified-before-every-execution",
                "provenance": "github-sigstore-attested",
            },
            "commands": list(runner.COMMANDS),
            "fixtures": fixture_records,
            "normalized_contract_sha256": hashlib.sha256(runner.canonical([
                {"case": record["case"], "normalized_result": record["normalized_result"]}
                for record in fixture_records
            ])).hexdigest(),
            "authority": {
                "phase6_live_evidence": "pending",
                "five_platform_equivalence": "pending",
                "platform_accepted": False,
                "phase7_accepted": False,
                "promotable": False,
                "production": False,
                "phase8": "closed",
                "blockers": list(runner.BLOCKERS),
            },
        }, artifact_identity

    five = []
    expected_artifacts = {}
    for platform in verifier.PLATFORMS:
        fixture_document, artifact_identity = independent_fixture_document(platform)
        five.append(fixture_document)
        expected_artifacts[platform] = artifact_identity
    verifier.verify_collection(five, True, expected_identity, expected_artifacts)

    substituted = deepcopy(five)
    for item in substituted:
        item["candidate"] = {
            "source_commit": "a" * 40,
            "source_tree": "b" * 40,
            "cargo_lock_sha256": "c" * 64,
            "command_binding_sha256": "d" * 64,
        }
        item["execution_workflow"] = {
            "path": verifier.WORKFLOW_PATH,
            "revision": "e" * 40,
            "sha256": "f" * 64,
        }
    try:
        verifier.verify_collection(substituted, True, expected_identity, expected_artifacts)
    except verifier.VerificationError:
        print("ok - rejected exact-five identity substitution")
    else:
        raise AssertionError("accepted mutually consistent substituted identities")

    try:
        verifier.verify_collection(five, True, expected_artifacts=expected_artifacts)
    except verifier.VerificationError:
        print("ok - rejected exact-five without external identity")
    else:
        raise AssertionError("accepted exact-five without external identity")

    try:
        verifier.verify_collection(five, True, expected_identity)
    except verifier.VerificationError:
        print("ok - rejected exact-five without verified build artifacts")
    else:
        raise AssertionError("accepted exact-five without verified build artifacts")

    for field, replacement in (
        ("platform", "macos-arm64"),
        ("runner", "ubuntu-24.04"),
        ("target", "x86_64-unknown-linux-gnu"),
        ("name", "harness-linux-x64"),
        ("sha256", "0" * 64),
    ):
        adversary = deepcopy(five)
        adversary[1]["artifact"][field] = replacement
        try:
            verifier.verify_collection(adversary, True, expected_identity, expected_artifacts)
        except verifier.VerificationError:
            print(f"ok - rejected build-receipt {field} substitution")
        else:
            raise AssertionError(f"accepted build-receipt {field} substitution")

    drifted = deepcopy(five)
    drifted[3]["fixtures"][0]["normalized_result"]["commands"][0]["outcome"] = "substituted"
    changed = drifted[3]["fixtures"][0]
    changed["normalized_sha256"] = hashlib.sha256(runner.canonical(changed["normalized_result"])).hexdigest()
    drifted[3]["normalized_contract_sha256"] = hashlib.sha256(runner.canonical([
        {"case": record["case"], "normalized_result": record["normalized_result"]}
        for record in drifted[3]["fixtures"]
    ])).hexdigest()
    try:
        verifier.verify_collection(drifted, True, expected_identity, expected_artifacts)
    except verifier.VerificationError:
        print("ok - rejected cross-platform normalized drift")
    else:
        raise AssertionError("accepted cross-platform normalized drift")
    for name, mutate in (
        ("provenance-substitution", lambda value: value["artifact"].update(provenance="checksum-only")),
        ("platform-overclaim", lambda value: value["authority"].update(platform_accepted=True)),
        ("normalized-drift", lambda value: value.update(normalized_contract_sha256="0" * 64)),
        ("normalized-payload-substitution", lambda value: value["fixtures"][0]["normalized_result"]["commands"][0].update(outcome="substituted")),
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
    refusal = 'Refuse "safe Windows destination publication is controlled-unsupported before mutation"'
    assert powershell.index("RuntimeInformation") < powershell.index(refusal)
    for prohibited in ("Copy-Item", "Move-Item", "[IO.File]::Move", "CreateDirectory", "New-Item", "Join-Path $Directory"):
        assert prohibited not in powershell
    assert "harness-windows-x64.exe" in powershell
    assert "Write-Output" not in powershell

    windows_refusal_test = (
        root / "tests/release/test-install-harness-v1-windows-unsupported.ps1"
    ).read_bytes()
    verifier.verify_windows_refusal_test(windows_refusal_test)

    for label, adversary in (
        (
            "required statements moved into a PowerShell block comment",
            b"<#\r\n" + windows_refusal_test + b"\r\n#>\r\n",
        ),
        (
            "comment-preserved disabled redirect and loose matching",
            windows_refusal_test.replace(
                b"$StartInfo.RedirectStandardError = $true",
                b"$StartInfo.RedirectStandardError = $false # $StartInfo.RedirectStandardError = $true",
                1,
            ).replace(
                b"$StandardError -ne $ExpectedStandardError",
                b'$StandardError -notlike "*$Expected*" # $StandardError -ne $ExpectedStandardError',
                1,
            ),
        ),
        (
            "native all-stream merge under ErrorActionPreference Stop",
            windows_refusal_test
            + b"\r\n$Output = & $PowerShellExe *>&1\r\n",
        ),
        (
            "forced successful exit assertion",
            windows_refusal_test.replace(
                b"$ExitCode = $Process.ExitCode",
                b"$ExitCode = 1 # $ExitCode = $Process.ExitCode",
                1,
            ),
        ),
        (
            "PowerShell minishell output format reverted to CLIXML",
            windows_refusal_test.replace(
                b"-OutputFormat Text",
                b"-OutputFormat XML",
                1,
            ),
        ),
        (
            "child progress suppression removed",
            windows_refusal_test.replace(
                b'$ProgressPreference = "SilentlyContinue"; & ',
                b"& ",
                1,
            ),
        ),
        (
            "child progress suppression weakened",
            windows_refusal_test.replace(
                b'$ProgressPreference = "SilentlyContinue"; & ',
                b'$ProgressPreference = "Continue"; & ',
                1,
            ),
        ),
        (
            "progress suppression set only in parent session",
            windows_refusal_test.replace(
                b"$Invocation = '$ProgressPreference = \"SilentlyContinue\"; & ",
                b'$ProgressPreference = "SilentlyContinue"\r\n$Invocation = \'& ',
                1,
            ),
        ),
        (
            "progress suppression moved after child installer invocation",
            windows_refusal_test.replace(
                b'$ProgressPreference = "SilentlyContinue"; & ',
                b"& ",
                1,
            ).replace(
                b" -Directory $env:HARNESS_V1_TEST_DESTINATION'\r\n$EncodedInvocation",
                b' -Directory $env:HARNESS_V1_TEST_DESTINATION; $ProgressPreference = "SilentlyContinue"\'\r\n$EncodedInvocation',
                1,
            ),
        ),
    ):
        try:
            verifier.verify_windows_refusal_test(adversary)
        except verifier.VerificationError:
            print(f"ok - rejected {label}")
        else:
            raise AssertionError(f"accepted {label}")

print("Phase 7 native execution proof covered all six commands and all ten fixtures without support claims")
PY

ending_status=$(git status --short --untracked-files=all)
if [[ "$ending_status" != "$starting_status" ]]; then
  printf 'Phase 7 execution focused test changed repository status\nbefore:\n%s\nafter:\n%s\n' \
    "$starting_status" "$ending_status" >&2
  exit 1
fi

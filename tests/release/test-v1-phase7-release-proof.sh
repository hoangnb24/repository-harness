#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
cd "$root"

fail() {
  echo "Phase 7 focused release-proof test failed: $*" >&2
  exit 1
}

for command in git python3; do
  command -v "$command" >/dev/null 2>&1 || fail "missing command: $command"
done

starting_git_status=$(git status --short --untracked-files=all)
temporary=$(mktemp -d "${TMPDIR:-/tmp}/phase7-release-proof.XXXXXX")
finish() {
  rm -rf "$temporary"
  ending_git_status=$(git status --short --untracked-files=all)
  [[ "$ending_git_status" == "$starting_git_status" ]] || {
    printf 'Phase 7 focused test changed repository status\nbefore:\n%s\nafter:\n%s\n' \
      "$starting_git_status" "$ending_git_status" >&2
    exit 1
  }
}
trap finish EXIT

scripts/verify-v1-phase7-release-proof.sh

set +e
schema_override_output=$(
  scripts/verify-v1-phase7-release-proof.sh \
    --schema release/contracts/v1/schemas/phase7-release-proof-v1.schema.json 2>&1
)
schema_override_exit=$?
set -e
[[ "$schema_override_exit" -eq 2 ]] || fail "production wrapper accepted or mishandled --schema"
[[ "$schema_override_output" == *"unrecognized arguments: --schema"* ]] || \
  fail "production wrapper did not reject --schema at the argument boundary"

set +e
pending_output=$(scripts/verify-v1-phase7-release-proof.sh --require-promotable 2>&1)
pending_exit=$?
set -e
[[ "$pending_exit" -eq 2 ]] || fail "require-promotable did not return pending exit 2"
[[ "$pending_output" == *"Phase 7 promotion blocked"* ]] || fail "require-promotable omitted the closed-gate reason"
[[ "$pending_output" == *"Phase 6 live evidence"* ]] || fail "require-promotable omitted deferred Phase 6"
[[ "$pending_output" == *"five Phase 7 platform results"* ]] || fail "require-promotable omitted pending Phase 7 results"

! grep -Eq '(^|[[:space:]])(subprocess|os\.system|popen|execv|spawn)[[:space:]\.(]' \
  scripts/verify_v1_phase7_release_proof.py || fail "verifier contains a command-execution primitive"

python3 - "$temporary" <<'PY'
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys


root = Path.cwd()
temporary = Path(sys.argv[1])
source_fixture = root / "tests/fixtures/v1-phase7"
schema = root / "release/contracts/v1/schemas/phase7-release-proof-v1.schema.json"
module_path = root / "scripts/verify_v1_phase7_release_proof.py"
spec = importlib.util.spec_from_file_location("phase7_release_proof", module_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def copied_case(name: str) -> tuple[Path, Path, dict]:
    case_root = temporary / name
    shutil.copytree(source_fixture, case_root)
    evidence = case_root / "phase7-release-proof.json"
    document = json.loads(evidence.read_text(encoding="utf-8"))
    return case_root, evidence, document


def reject_document(name: str, mutate) -> None:
    case_root, evidence, document = copied_case(name)
    mutate(document, case_root)
    evidence.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        module.verify(evidence, schema, case_root, False)
    except module.VerificationError:
        print(f"ok - rejected {name}")
        return
    raise AssertionError(f"accepted adversary: {name}")


case_root, evidence, _ = copied_case("duplicate-key")
payload = evidence.read_text(encoding="utf-8")
needle = '  "schema": "repository-harness-v1-phase7-release-proof/v1",\n'
assert payload.count(needle) == 1
evidence.write_text(payload.replace(needle, needle + needle, 1), encoding="utf-8")
try:
    module.verify(evidence, schema, case_root, False)
except module.VerificationError:
    print("ok - rejected duplicate-key")
else:
    raise AssertionError("accepted duplicate JSON key")


reject_document("missing-platform", lambda document, _: document["artifacts"].pop())
reject_document(
    "duplicate-platform",
    lambda document, _: document["artifacts"][1].update(
        platform=document["artifacts"][0]["platform"]
    ),
)
reject_document(
    "artifact-checksum-collision",
    lambda document, _: document["artifacts"][0].update(
        checksum=document["artifacts"][0]["artifact"],
        checksum_sha256=document["artifacts"][0]["artifact_sha256"],
    ),
)
reject_document(
    "v0-harness-cli-identity-crossover",
    lambda document, _: document["artifacts"][0].update(
        artifact="artifacts/harness-cli-macos-arm64",
        checksum="artifacts/harness-cli-macos-arm64.sha256",
    ),
)


def checksum_drift(_, case_root: Path) -> None:
    path = case_root / "artifacts/harness-linux-x64.sha256"
    path.write_bytes(path.read_bytes().replace(b"f75f", b"075f", 1))


reject_document("checksum-drift", checksum_drift)
reject_document(
    "missing-candidate-field",
    lambda document, _: document["candidate"].pop("payload_index_sha256"),
)
reject_document(
    "candidate-drift",
    lambda document, _: document["artifacts"][3]["candidate"].update(
        source_revision="0" * 40
    ),
)


def replace_candidate_identity(document: dict, field: str, value: str) -> None:
    document["candidate"][field] = value
    for artifact in document["artifacts"]:
        artifact["candidate"][field] = value


for field, value in (
    ("v1_cli_identity", "harness-cli-v0/legacy-crossover"),
    ("template_release", "repository-harness-template/relabeled"),
    ("bridge_identity", "harness-cli/relabeled-bridge"),
):
    reject_document(
        f"semantic-identity-{field}",
        lambda document, _, field=field, value=value: replace_candidate_identity(
            document, field, value
        ),
    )


def platform_evidence_pass_claim(document: dict, _: Path) -> None:
    document["evidence_kind"] = "platform-evidence-non-production"
    artifact = document["artifacts"][0]
    artifact["authentication"].update(
        state="authenticated", evidence=["nonexistent/authentication.json"]
    )
    for field in ("build_result", "direct_binary_result", "installer_result"):
        artifact[field].update(state="passed", evidence=[f"nonexistent/{field}.json"])


reject_document("platform-evidence-pass-claims", platform_evidence_pass_claim)


def missing_fixture(_, case_root: Path) -> None:
    (case_root / "repositories/docs-only/docs/guide.md").unlink()


def fixture_hash_drift(_, case_root: Path) -> None:
    path = case_root / "repositories/crlf/line-endings.txt"
    path.write_bytes(path.read_bytes() + b"drift\r\n")


reject_document("missing-fixture", missing_fixture)
reject_document("fixture-hash-drift", fixture_hash_drift)

for field, value in (
    ("phase7_acceptance", "accepted"),
    ("promotable", True),
    ("tag_authorized", True),
    ("publish_authorized", True),
    ("promotion_authorized", True),
    ("production_signing_authorized", True),
):
    reject_document(
        f"unsafe-{field}",
        lambda document, _, field=field, value=value: document["promotion"].update(
            {field: value}
        ),
    )


marker = temporary / "evidence-command-ran"


def command_claim(document: dict, _: Path) -> None:
    document["artifacts"][0]["build_result"]["command"] = f"touch {marker}"


reject_document("evidence-command", command_claim)
assert not marker.exists(), "verifier executed a command supplied by evidence"

print("Phase 7 same-filename temporary-copy adversaries passed")
PY

echo "Phase 7 focused release-proof contract passed and remains non-promotable"

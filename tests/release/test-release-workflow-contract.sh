#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
release="$root/.github/workflows/harness-cli-release.yml"
post_merge="$root/.github/workflows/post-merge-maintenance.yml"
premerge="$root/.github/workflows/premerge.yml"

fail() {
  echo "release workflow contract failed: $*" >&2
  exit 1
}

python3 - "$premerge" <<'PY'
from pathlib import Path
import sys


workflow = Path(sys.argv[1]).read_text(encoding="utf-8")
toolchain = "          toolchain: 1.97.0\n"
expected = (
    "env:\n"
    "  CARGO_TERM_COLOR: always\n"
    '  PYTHONDONTWRITEBYTECODE: "1"\n'
    "\n"
    "jobs:\n"
)


def verify(source: str) -> None:
    if source.count(toolchain) != 2:
        raise ValueError("Pre-Merge Rust toolchain is not pinned for both jobs")
    if source.count("PYTHONDONTWRITEBYTECODE") != 1:
        raise ValueError("Pre-Merge bytecode setting is missing or ambiguous")
    if source.count(expected) != 1:
        raise ValueError("Pre-Merge bytecode setting is not workflow-global")


verify(workflow)

fmt = "cargo fmt --all -- --check"
clippy = "cargo clippy --workspace --all-targets --locked -- -D warnings"
phase1 = "scripts/verify-v1-phase1-contracts.sh"
if not workflow:
    raise ValueError("Pre-Merge workflow is empty")

premerge_script = Path(sys.argv[1]).parents[2] / "scripts/validate-premerge.sh"
premerge = premerge_script.read_text(encoding="utf-8")
if not (premerge.index(fmt) < premerge.index(clippy) < premerge.index(phase1)):
    raise ValueError("Pre-Merge fmt and Clippy gates do not fail fast")

adversaries = {
    "missing": workflow.replace('  PYTHONDONTWRITEBYTECODE: "1"\n', "", 1),
    "false-value": workflow.replace(
        '  PYTHONDONTWRITEBYTECODE: "1"',
        '  PYTHONDONTWRITEBYTECODE: "0"',
        1,
    ),
    "comment-only": workflow.replace(
        '  PYTHONDONTWRITEBYTECODE: "1"',
        '# PYTHONDONTWRITEBYTECODE: "1"',
        1,
    ),
    "job-only": workflow.replace(
        '  PYTHONDONTWRITEBYTECODE: "1"\n',
        "",
        1,
    ).replace(
        "  validate:\n",
        '  validate:\n    env:\n      PYTHONDONTWRITEBYTECODE: "1"\n',
        1,
    ),
}
for name, adversary in adversaries.items():
    try:
        verify(adversary)
    except ValueError:
        continue
    raise AssertionError(f"accepted premerge bytecode adversary: {name}")
PY

[[ "$(grep -Ec '^          - platform: (macos-arm64|macos-x64|linux-x64|linux-arm64|windows-x64)$' "$release")" == 5 ]]
for platform in macos-arm64 macos-x64 linux-x64 linux-arm64 windows-x64; do
  grep -Fq -- "- platform: $platform" "$release"
done

grep -Fq 'run: scripts/validate-premerge.sh' "$release"
grep -Fq 'source_sha: ${{ steps.source.outputs.sha }}' "$release"
grep -Fq 'ref: ${{ needs.verify.outputs.source_sha }}' "$release"
grep -Fq 'needs: [verify, build]' "$release"
grep -Fq 'scripts/verify-harness-cli-release-identity.sh' "$release"
grep -Fq 'pretag "$RELEASE_TAG" "$SOURCE_SHA" "$PROOF_RUN"' "$release"
grep -Fq 'scripts/promote-harness-cli-release-tag.sh' "$release"
grep -Fq -- '--verify-tag' "$release"
grep -Fq 'test "$(gh release view "$RELEASE_TAG"' "$release"
! grep -Fq -- '--clobber' "$release"
! grep -Eq '^  push:' "$release"
! grep -Fq 'git tag ' "$release"

grep -Fq 'tests/release/download-v0.1.14-artifact.sh' "$release"
grep -Fq 'tests/installer/test-cli-upgrade-candidate.sh' "$release"
grep -Fq 'tests/installer/test-install-harness-modes.ps1' "$release"
grep -Fq 'tests/protocol/smoke-native-artifact.sh' "$release"
grep -Fq 'tests/protocol/smoke-native-artifact.ps1' "$release"

! grep -Fq 'git tag ' "$post_merge"
! grep -Fq 'git push origin "$release_tag"' "$post_merge"
grep -Fq 'checkout_ref: ${{ needs.prepare.outputs.maintenance_ref }}' "$post_merge"
grep -Fq 'Harness CLI candidate:' "$post_merge"

[[ "$(grep -Fc 'fetch-depth: 0' "$premerge")" -eq 2 ]]
grep -Fq 'Prove Linux initial-to-candidate upgrade' "$premerge"
grep -Fq 'Download pinned Windows initial protocol artifact' "$premerge"
grep -Fq 'test-cli-upgrade-candidate.sh' "$premerge"
grep -Fq -- '-InitialArtifact dist/us092-harness-cli-windows-x64.exe' "$premerge"

temporary=$(mktemp -d "${TMPDIR:-/tmp}/premerge-bytecode-contract.XXXXXX")
cleanup() {
  rm -rf "$temporary"
}
trap cleanup EXIT
control_checkout="$temporary/control-checkout"
git clone --quiet --no-hardlinks "$root" "$control_checkout"

control_starting_status=$(git -C "$control_checkout" status --short --untracked-files=all)
[[ -z "$control_starting_status" ]] || fail "negative-control checkout did not start clean"
set +e
control_output=$(
  (
    cd "$control_checkout"
    unset PYTHONDONTWRITEBYTECODE
    export PYTHONPYCACHEPREFIX="$control_checkout/.premerge-pycache"
    PYTHONPATH="$control_checkout/scripts" python3 -c 'import verify_v1_phase2_core'
    tests/release/test-v1-phase7-release-proof.sh
  ) 2>&1
)
control_exit=$?
set -e
[[ "$control_exit" -ne 0 ]] || fail "unguarded import sequence unexpectedly stayed clean"
[[ "$control_output" == *"Phase 7 focused test changed repository status"* ]] || \
  fail "unguarded import sequence did not trigger the Phase 7 status trap"
if ! find "$control_checkout" -type f -name '*.pyc' -print -quit | grep -q .; then
  fail "unguarded import sequence did not create in-checkout Python bytecode"
fi
control_ending_status=$(git -C "$control_checkout" status --short --untracked-files=all)
[[ "$control_ending_status" != "$control_starting_status" ]] || \
  fail "unguarded import sequence did not change Git status"

guarded_checkout="$temporary/guarded-checkout"
git clone --quiet --no-hardlinks "$root" "$guarded_checkout"

guarded_starting_status=$(git -C "$guarded_checkout" status --short --untracked-files=all)
[[ -z "$guarded_starting_status" ]] || fail "guarded checkout did not start clean"
if find "$guarded_checkout" \( -type d -name __pycache__ -o -type f -name '*.pyc' \) \
  -print -quit | grep -q .; then
  fail "guarded checkout unexpectedly contains Python bytecode"
fi

(
  cd "$guarded_checkout"
  export PYTHONPYCACHEPREFIX="$guarded_checkout/.premerge-pycache"
  export PYTHONDONTWRITEBYTECODE=1
  PYTHONPATH="$guarded_checkout/scripts" python3 -c 'import verify_v1_phase2_core'
  tests/release/test-v1-phase7-release-proof.sh
)

if find "$guarded_checkout" \( -type d -name __pycache__ -o -type f -name '*.pyc' \) \
  -print -quit | grep -q .; then
  fail "premerge Python entry points created repository bytecode"
fi
guarded_ending_status=$(git -C "$guarded_checkout" status --short --untracked-files=all)
[[ "$guarded_ending_status" == "$guarded_starting_status" ]] || {
  printf 'isolated premerge entry points changed repository status\nbefore:\n%s\nafter:\n%s\n' \
    "$guarded_starting_status" "$guarded_ending_status" >&2
  exit 1
}

echo "five-platform proof-before-promotion, immutable release, and pre-merge transition workflow contract passed"

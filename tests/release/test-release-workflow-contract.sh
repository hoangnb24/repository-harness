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
expected = (
    "env:\n"
    "  CARGO_TERM_COLOR: always\n"
    '  PYTHONDONTWRITEBYTECODE: "1"\n'
    "\n"
    "jobs:\n"
)


def verify(source: str) -> None:
    if source.count("PYTHONDONTWRITEBYTECODE") != 1:
        raise ValueError("Pre-Merge bytecode setting is missing or ambiguous")
    if source.count(expected) != 1:
        raise ValueError("Pre-Merge bytecode setting is not workflow-global")


verify(workflow)

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
checkout="$temporary/checkout"
git clone --quiet --no-hardlinks "$root" "$checkout"

starting_status=$(git -C "$checkout" status --short --untracked-files=all)
[[ -z "$starting_status" ]] || fail "isolated checkout did not start clean"
if find "$checkout" \( -type d -name __pycache__ -o -type f -name '*.pyc' \) \
  -print -quit | grep -q .; then
  fail "isolated checkout unexpectedly contains Python bytecode"
fi

(
  cd "$checkout"
  unset PYTHONPYCACHEPREFIX
  export PYTHONDONTWRITEBYTECODE=1
  PYTHONPATH="$checkout/scripts" python3 -c 'import verify_v1_phase2_core'
  tests/release/test-v1-phase7-release-proof.sh
)

if find "$checkout" \( -type d -name __pycache__ -o -type f -name '*.pyc' \) \
  -print -quit | grep -q .; then
  fail "premerge Python entry points created repository bytecode"
fi
ending_status=$(git -C "$checkout" status --short --untracked-files=all)
[[ "$ending_status" == "$starting_status" ]] || {
  printf 'isolated premerge entry points changed repository status\nbefore:\n%s\nafter:\n%s\n' \
    "$starting_status" "$ending_status" >&2
  exit 1
}

echo "five-platform proof-before-promotion, immutable release, and pre-merge transition workflow contract passed"

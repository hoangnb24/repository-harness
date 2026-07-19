#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
workflow="$root/.github/workflows/harness-v1-release.yml"

fail() {
  echo "V1 build-receipt workflow contract failed: $*" >&2
  exit 1
}

[[ "$(grep -Ec '^          - platform: (macos-arm64|macos-x64|linux-x64|linux-arm64|windows-x64)$' "$workflow")" == 5 ]] ||
  fail "workflow does not contain exactly five supported platform rows"
for tuple in \
  'macos-arm64|aarch64-apple-darwin|macos-15' \
  'macos-x64|x86_64-apple-darwin|macos-15-intel' \
  'linux-x64|x86_64-unknown-linux-gnu|ubuntu-24.04' \
  'linux-arm64|aarch64-unknown-linux-gnu|ubuntu-24.04-arm' \
  'windows-x64|x86_64-pc-windows-msvc|windows-latest'; do
  IFS='|' read -r platform target runner <<<"$tuple"
  grep -A2 -F -- "- platform: $platform" "$workflow" |
    grep -Fq "target: $target" || fail "target drift for $platform"
  grep -A2 -F -- "- platform: $platform" "$workflow" |
    grep -Fq "runner: $runner" || fail "runner drift for $platform"
done

grep -Fq 'resolve-candidate:' "$workflow" || fail "candidate resolver job is missing"
grep -Fq 'candidate_sha: ${{ steps.resolve.outputs.candidate_sha }}' "$workflow" || fail "resolver output is missing"
grep -Fq "candidate_sha=\$candidate_sha" "$workflow" || fail "immutable SHA handoff is missing"
grep -Fq 'ref: refactor/harness-v1' "$workflow" || fail "resolver does not start from the approved branch"
grep -Fq 'refs/remotes/origin/refactor/harness-v1' "$workflow" || fail "approved remote branch policy is missing"
grep -Fq 'git merge-base --is-ancestor "$candidate_sha" refs/remotes/origin/refactor/harness-v1' "$workflow" ||
  fail "candidate reachability proof is missing"
grep -Fq 'fetch-depth: 0' "$workflow" || fail "full history required for reachability is missing"
[[ "$(grep -Fc 'persist-credentials: false' "$workflow")" == 3 ]] ||
  fail "resolver, matrix, and collector must all disable persisted checkout credentials"
[[ "$(grep -Fc 'ref: ${{ needs.resolve-candidate.outputs.candidate_sha }}' "$workflow")" == 2 ]] ||
  fail "matrix and collector do not both checkout the immutable resolver SHA"

grep -Fq 'CANDIDATE_REF: ${{ inputs.candidate_ref }}' "$workflow" || fail "candidate input is not mapped through env"
! grep -Fq 'test "${{ inputs.candidate_ref }}"' "$workflow" || fail "candidate input is interpolated into shell source"
grep -Fq 'git rev-parse --verify --end-of-options "${CANDIDATE_REF}^{commit}"' "$workflow" ||
  fail "candidate input is not passed as one end-of-options-protected argv value"
grep -Fq 'WORKFLOW_REVISION: ${{ github.workflow_sha }}' "$workflow" || fail "immutable execution-workflow SHA is missing"
[[ "$(grep -Fc -- '--workflow-revision "$WORKFLOW_REVISION"' "$workflow")" == 2 ]] ||
  fail "capture and collector do not share the execution-workflow revision"
[[ "$(grep -Fc 'refs/heads/main:refs/remotes/origin/main' "$workflow")" == 2 ]] ||
  fail "matrix and collector do not fetch protected main for workflow object verification"
[[ "$(grep -Fc 'git cat-file -e "${WORKFLOW_REVISION}:.github/workflows/harness-v1-release.yml"' "$workflow")" == 2 ]] ||
  fail "matrix and collector do not prove exact workflow bytes exist at the execution revision"

matrix_block=$(sed -n '/^  prove-before-promotion:/,/^  collect-receipts:/p' "$workflow")
[[ "$matrix_block" != *'inputs.candidate_ref'* ]] || fail "matrix checkout still uses the mutable input ref"
[[ "$matrix_block" == *'actions/setup-python@v5'* && "$matrix_block" == *"python-version: '3.12'"* ]] ||
  fail "matrix does not pin a cross-platform Python runtime"
[[ "$matrix_block" == *'scripts/capture-v1-build-receipt.sh'* ]] || fail "matrix does not use the capture script"
[[ "$matrix_block" == *'actions/upload-artifact@v4'* ]] || fail "receipt upload is missing"
[[ "$matrix_block" == *'retention-days: 5'* ]] || fail "explicit short retention is missing"

grep -Fq 'actions/download-artifact@v4' "$workflow" || fail "receipt download is missing"
grep -Fq 'pattern: harness-v1-build-receipt-*' "$workflow" || fail "exact receipt download pattern is missing"
grep -Fq 'scripts/verify-v1-build-receipts.sh' "$workflow" || fail "collector verifier is missing"
grep -Fq -- '--require-five' "$workflow" || fail "collector does not require all five platforms"
grep -Fq 'needs: collect-receipts' "$workflow" || fail "promotion guard is not downstream of collection"
grep -Fq 'exit 1' "$workflow" || fail "promotion guard no longer fails closed"
grep -Fq 'contents: read' "$workflow" || fail "workflow lacks contents-read permission"

! grep -Eq 'contents:[[:space:]]*write|id-token:|packages:[[:space:]]*write|actions/attest|sigstore|gh release|git tag|git push|cargo publish|npm publish' "$workflow" ||
  fail "workflow contains release, publish, OIDC, signing, or attestation authority"

grep -Fq 'hoangnb24/repository-harness/.github/workflows/harness-v1-release.yml@refs/heads/main' "$workflow" ||
  fail "main-workflow identity pin is missing"

echo "V1 exact five-platform immutable build-receipt workflow contract passed; release authority remains absent"

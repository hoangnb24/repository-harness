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
grep -Fq 'ref: ${{ github.sha }}' "$workflow" || fail "resolver does not start from the immutable dispatch SHA"
grep -Fq 'push:' "$workflow" || fail "diagnostic workflow is not push-discoverable"
grep -Fq -- '- refactor/harness-v1' "$workflow" || fail "diagnostic workflow is not scoped to refactor/harness-v1"
grep -Fq -- '- .github/harness-v1-diagnostic-request' "$workflow" || fail "diagnostic workflow lacks its cost-control sentinel path"
! grep -Fq 'workflow_dispatch:' "$workflow" || fail "workflow remains manual-dispatch-only"
! grep -Fq 'candidate_ref' "$workflow" || fail "workflow still accepts an arbitrary candidate"
! grep -Fq 'refs/heads/agent/' "$workflow" || fail "workflow still grants agent-branch diagnostic authority"
! grep -Fq '@refs/heads/main' "$workflow" || fail "workflow still requires default-branch discovery"
grep -Fq 'test "$REPOSITORY" = hoangnb24/repository-harness' "$workflow" || fail "repository identity check is missing"
grep -Fq 'test "$EVENT_NAME" = push' "$workflow" || fail "event identity check is missing"
grep -Fq 'test "$PUSH_REF" = refs/heads/refactor/harness-v1' "$workflow" || fail "push ref identity check is missing"
grep -Fq 'test "$WORKFLOW_REF" = hoangnb24/repository-harness/.github/workflows/harness-v1-release.yml@refs/heads/refactor/harness-v1' "$workflow" ||
  fail "workflow ref identity check is missing"
grep -Fq 'test "$CANDIDATE_SHA" = "$WORKFLOW_REVISION"' "$workflow" ||
  fail "push candidate is not identical to the executing workflow revision"
grep -Fq 'refs/remotes/origin/refactor/harness-v1' "$workflow" || fail "approved remote branch policy is missing"
grep -Fq 'fetch-depth: 0' "$workflow" || fail "full history required for reachability is missing"
[[ "$(grep -Fc 'persist-credentials: false' "$workflow")" == 3 ]] ||
  fail "resolver, matrix, and collector must all disable persisted checkout credentials"
[[ "$(grep -Fc 'ref: ${{ needs.resolve-candidate.outputs.candidate_sha }}' "$workflow")" == 2 ]] ||
  fail "matrix and collector do not both checkout the immutable resolver SHA"

grep -Fq 'WORKFLOW_REVISION: ${{ github.workflow_sha }}' "$workflow" || fail "immutable execution-workflow SHA is missing"
[[ "$(grep -Fc -- '--workflow-revision "$WORKFLOW_REVISION"' "$workflow")" == 4 ]] ||
  fail "build/execution capture and both collectors do not share the execution-workflow revision"
[[ "$(grep -Fc 'refs/remotes/origin/workflow-execution' "$workflow")" == 4 ]] ||
  fail "matrix and collector do not fetch and compare the exact workflow ref"
[[ "$(grep -Fc 'git cat-file -e "${WORKFLOW_REVISION}:.github/workflows/harness-v1-release.yml"' "$workflow")" == 2 ]] ||
  fail "matrix and collector do not prove exact workflow bytes exist at the execution revision"

matrix_block=$(sed -n '/^  prove-before-promotion:/,/^  collect-receipts:/p' "$workflow")
[[ "$matrix_block" != *'inputs.candidate_ref'* ]] || fail "matrix checkout still uses the mutable input ref"
[[ "$matrix_block" == *'actions/setup-python@v5'* && "$matrix_block" == *"python-version: '3.12'"* ]] ||
  fail "matrix does not pin a cross-platform Python runtime"
[[ "$matrix_block" == *'scripts/capture-v1-build-receipt.sh'* ]] || fail "matrix does not use the capture script"
[[ "$matrix_block" == *'scripts/run_v1_phase7_execution_proof.py'* ]] || fail "matrix does not run the six-command fixture proof"
[[ "$matrix_block" == *'behavior: controlled-unsupported-before-mutation'* ]] ||
  fail "Windows row fabricates successful mutation instead of controlled unsupported behavior"
[[ "$matrix_block" == *'tests/release/test-install-harness-v1-destination.ps1'* ]] ||
  fail "Windows row lacks native destination-junction adversaries"
[[ "$matrix_block" == *'.authority.five_platform_equivalence == "pending"'* ]] ||
  fail "matrix no longer verifies that five-platform equivalence remains pending"
[[ "$matrix_block" == *'scripts/install-harness-v1.ps1'* || "$matrix_block" == *'scripts/prepare-v1-phase7-test-release.py'* ]] ||
  fail "matrix does not prepare external signed test input for installer proof"
[[ "$matrix_block" == *'actions/upload-artifact@v4'* ]] || fail "receipt upload is missing"
[[ "$matrix_block" == *'retention-days: 5'* ]] || fail "explicit short retention is missing"

grep -Fq 'actions/download-artifact@v4' "$workflow" || fail "receipt download is missing"
grep -Fq 'pattern: harness-v1-build-receipt-*' "$workflow" || fail "exact receipt download pattern is missing"
[[ "$(grep -Fc 'merge-multiple: false' "$workflow")" == 2 ]] ||
  fail "build and execution collection must preserve one directory per platform artifact"
[[ "$(grep -Fc 'path: ${{ runner.temp }}/harness-v1-build-receipts' "$workflow")" == 1 ]] ||
  fail "receipt download root is missing or ambiguous"
grep -Fq 'RECEIPT_ROOT: ${{ runner.temp }}/harness-v1-build-receipts' "$workflow" ||
  fail "collector verifier root does not match the runner-temp download root"
grep -Fq '"$RECEIPT_ROOT"' "$workflow" || fail "collector does not pass its mapped download root to the verifier"
! grep -Fq '"$RUNNER_TEMP/harness-v1-build-receipts"' "$workflow" ||
  fail "collector verifier bypasses the shared cross-platform receipt-root mapping"
grep -Fq 'scripts/verify-v1-build-receipts.sh' "$workflow" || fail "collector verifier is missing"
grep -Fq 'scripts/verify-v1-phase7-execution-proof.sh --require-five' "$workflow" ||
  grep -Fq -- '--require-five' "$workflow" || fail "exact-five execution verifier is missing"
grep -Fq -- '--candidate "$CANDIDATE_SHA"' "$workflow" || fail "exact-five verifier lacks external candidate identity"
grep -Fq -- '--workflow-revision "$WORKFLOW_REVISION"' "$workflow" || fail "exact-five verifier lacks external workflow revision"
grep -Fq -- '--repository-root "$REPOSITORY_ROOT"' "$workflow" || fail "exact-five verifier cannot recompute committed identity bytes"
grep -Fq 'pattern: harness-v1-execution-proof-*' "$workflow" ||
  fail "execution-proof download inventory is missing"
grep -Fq -- '--require-five' "$workflow" || fail "collector does not require all five platforms"
grep -Fq 'contents: read' "$workflow" || fail "workflow lacks contents-read permission"
grep -Fq "if: github.repository == 'hoangnb24/repository-harness'" "$workflow" || fail "workflow-level repository guard is missing"
grep -Fq 'promotion-blocked:' "$workflow" || fail "fail-closed promotion guard is missing"
grep -Fq 'needs: collect-receipts' "$workflow" || fail "promotion guard is not downstream of diagnostics"
grep -Fq 'repository-protection and pinned artifact-attestation evidence are not present' "$workflow" ||
  fail "promotion guard lost its external-evidence refusal"

! grep -Eq 'contents:[[:space:]]*write|id-token:|packages:[[:space:]]*write|actions/attest|sigstore|gh release|git tag|git push|cargo publish|npm publish' "$workflow" ||
  fail "workflow contains release, publish, OIDC, signing, or attestation authority"

! grep -Eq 'request_promotion|inputs\.' "$workflow" ||
  fail "diagnostic workflow retains arbitrary-input authority"

echo "V1 refactor-branch immutable diagnostic workflow contract passed; Windows equivalence and release authority remain blocked"

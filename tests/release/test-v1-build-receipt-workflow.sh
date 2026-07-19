#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
workflow="$root/.github/workflows/harness-v1-release.yml"

fail() {
  echo "V1 build-receipt workflow contract failed: $*" >&2
  exit 1
}

[[ "$(grep -Ec '^          - platform: (macos-arm64|macos-x64|linux-x64|linux-arm64|windows-x64)$' "$workflow")" == 15 ]] ||
  fail "build, attestation, and verify/execute jobs do not each contain the exact five supported platforms"
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
[[ "$(grep -Fc 'persist-credentials: false' "$workflow")" == 4 ]] ||
  fail "resolver, build, verify/execute, and collector must disable persisted checkout credentials"
[[ "$(grep -Fc 'ref: ${{ needs.resolve-candidate.outputs.candidate_sha }}' "$workflow")" == 3 ]] ||
  fail "build, verify/execute, and collector do not checkout the immutable resolver SHA"

grep -Fq 'WORKFLOW_REVISION: ${{ github.workflow_sha }}' "$workflow" || fail "immutable execution-workflow SHA is missing"
[[ "$(grep -Fc -- '--workflow-revision "$WORKFLOW_REVISION"' "$workflow")" == 5 ]] ||
  fail "build, finalization, execution, Windows guard, and both collectors do not share the workflow revision"
[[ "$(grep -Fc 'refs/remotes/origin/workflow-execution' "$workflow")" == 6 ]] ||
  fail "build, verify/execute, and collector do not fetch and compare the exact workflow ref"
[[ "$(grep -Fc 'git cat-file -e "${WORKFLOW_REVISION}:.github/workflows/harness-v1-release.yml"' "$workflow")" == 3 ]] ||
  fail "build, verify/execute, and collector do not prove exact workflow bytes"

build_block=$(sed -n '/^  build-native-artifact:/,/^  attest-native-artifact:/p' "$workflow")
attest_block=$(sed -n '/^  attest-native-artifact:/,/^  verify-execute-native-proof:/p' "$workflow")
execute_block=$(sed -n '/^  verify-execute-native-proof:/,/^  collect-receipts:/p' "$workflow")
[[ "$build_block$attest_block$execute_block" != *'inputs.candidate_ref'* ]] || fail "native jobs use a mutable input ref"
[[ "$build_block" == *'actions/setup-python@v5'* && "$execute_block" == *'actions/setup-python@v5'* ]] ||
  fail "build and verify/execute jobs do not pin cross-platform Python"
[[ "$build_block" == *'steps.python.outputs.python-path }}" scripts/capture_v1_build_receipt.py'* ]] ||
  fail "build bypasses the setup-python output"
[[ "$attest_block" == *'actions/attest-build-provenance@96278af6caaf10aea03fd8d33a09a777ca52d62f'* ]] ||
  fail "isolated attestation job does not use the exact v3.2.0 commit"
[[ "$attest_block" != *'scripts/run_v1_phase7_execution_proof.py'* ]] ||
  fail "attestation job can execute candidate code"
[[ "$execute_block" == *'steps.python.outputs.python-path }}" scripts/finalize_v1_build_receipt.py'* ]] ||
  fail "verify/execute job bypasses explicit Python for finalization"
[[ "$execute_block" == *'--build-receipt-directory "$RECEIPT_OUTPUT"'* ]] ||
  fail "execution runner does not repeat exact build-receipt provenance verification"
[[ "$execute_block" == *'steps.python.outputs.python-path }}" scripts/run_v1_phase7_execution_proof.py'* ]] ||
  fail "verify/execute job does not use explicit Python for the execution proof"
[[ "$execute_block" == *'behavior: controlled-unsupported-before-mutation'* ]] ||
  fail "Windows row fabricates successful mutation instead of controlled unsupported behavior"
[[ "$execute_block" == *'tests/release/test-install-harness-v1-windows-unsupported.ps1'* ]] ||
  fail "Windows row lacks native controlled-unsupported-before-mutation proof"
[[ "$execute_block" == *'--target "${{ matrix.target }}"'* ]] ||
  fail "execution proof is not bound to the build target"
[[ "$execute_block" == *'--runner "${{ matrix.runner }}"'* ]] ||
  fail "execution proof is not bound to the build runner"
[[ "$execute_block" == *'.authority.five_platform_equivalence == "pending"'* ]] ||
  fail "matrix no longer verifies that five-platform equivalence remains pending"
[[ "$execute_block" == *'scripts/install-harness-v1.ps1'* || "$execute_block" == *'scripts/prepare-v1-phase7-test-release.py'* ]] ||
  fail "matrix does not prepare external signed test input for installer proof"
[[ "$build_block$execute_block" == *'actions/upload-artifact@v4'* ]] || fail "read-only artifact upload is missing"
[[ "$attest_block" == *'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a'* ]] ||
  fail "privileged bundle upload is not pinned to verified v7.0.1"
[[ "$build_block$attest_block$execute_block" == *'retention-days: 5'* ]] || fail "explicit short retention is missing"

grep -Fq 'actions/download-artifact@v4' "$workflow" || fail "read-only receipt download is missing"
[[ "$attest_block" == *'actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c'* ]] ||
  fail "privileged artifact download is not pinned to verified v8.0.1"
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
grep -Fq 'steps.python.outputs.python-path }}" scripts/verify_v1_build_receipts.py' "$workflow" || fail "collector explicit Python verifier is missing"
grep -Fq 'scripts/verify-v1-phase7-execution-proof.sh --require-five' "$workflow" ||
  grep -Fq -- '--require-five' "$workflow" || fail "exact-five execution verifier is missing"
grep -Fq -- '--candidate "$CANDIDATE_SHA"' "$workflow" || fail "exact-five verifier lacks external candidate identity"
grep -Fq -- '--workflow-revision "$WORKFLOW_REVISION"' "$workflow" || fail "exact-five verifier lacks external workflow revision"
grep -Fq -- '--repository-root "$REPOSITORY_ROOT"' "$workflow" || fail "exact-five verifier cannot recompute committed identity bytes"
grep -Fq 'BUILD_RECEIPT_ROOT: ${{ runner.temp }}/harness-v1-build-receipts' "$workflow" ||
  fail "execution collector does not reuse the verified build-receipt root"
grep -Fq -- '--build-receipt-root "$BUILD_RECEIPT_ROOT"' "$workflow" ||
  fail "exact-five verifier is not cross-bound to verified build receipts"
grep -Fq 'pattern: harness-v1-execution-proof-*' "$workflow" ||
  fail "execution-proof download inventory is missing"
grep -Fq -- '--require-five' "$workflow" || fail "collector does not require all five platforms"
grep -Fq 'contents: read' "$workflow" || fail "workflow lacks contents-read permission"
! grep -Fq "if: github.repository == 'hoangnb24/repository-harness'" "$workflow" ||
  fail "foreign repositories can skip benignly through a job-level repository guard"
! grep -Eiq '^  [^#[:space:]][^:]*(promotion|release|publish|sign|tag)[^:]*:' "$workflow" ||
  fail "diagnostic workflow contains a promotion or release-authority job/path"
! grep -Fq 'promotion-blocked:' "$workflow" || fail "diagnostic workflow contains a failing promotion job"

python3 "$root/scripts/verify_v1_attestation_workflow.py" "$workflow" >/dev/null ||
  fail "workflow violates the exact-pinned least-privilege attestation boundary"
! grep -Eiq 'contents:[[:space:]]*write|packages:[[:space:]]*write|actions/create-release|softprops/action-gh-release|ncipollo/release-action|gh[[:space:]]+release|git[[:space:]]+tag|git[[:space:]]+push|cargo[[:space:]]+publish|npm[[:space:]]+publish|cosign|gpg[[:space:]]+--sign' "$workflow" ||
  fail "workflow contains release, publish, or production-signing authority"

! grep -Eq 'request_promotion|inputs\.' "$workflow" ||
  fail "diagnostic workflow retains arbitrary-input authority"

echo "V1 refactor-branch GitHub/Sigstore-attested diagnostic workflow contract passed; Windows equivalence and release authority remain blocked"

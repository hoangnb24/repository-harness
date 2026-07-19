#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"

fail() {
  echo "pre-merge validation: $*" >&2
  exit 1
}

(( $# == 0 )) || fail "arguments are not accepted; use the paired Phase 5 trust environment variables"

while IFS= read -r variable; do
  case "$variable" in
    HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY|HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256) ;;
    *) fail "unknown Phase 5 environment option: $variable" ;;
  esac
done < <(compgen -A variable HARNESS_PHASE5_ || true)

registry_is_set=${HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY+x}
registry_sha_is_set=${HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256+x}
[[ "$registry_is_set" == "$registry_sha_is_set" ]] || fail "Phase 5 trust registry path and SHA-256 must be supplied together"

phase5_arguments=()
if [[ -n "$registry_is_set" ]]; then
  registry=$HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY
  registry_sha=$HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256
  [[ "$registry" == /* ]] || fail "Phase 5 trust registry path must be absolute"
  [[ "$registry_sha" =~ ^[0-9a-f]{64}$ ]] || fail "Phase 5 trust registry SHA-256 must be 64 lowercase hexadecimal characters"
  phase5_arguments=(
    --trusted-owner-registry "$registry"
    --trusted-owner-registry-sha256 "$registry_sha"
  )
fi
unset HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256

for command in cargo git jq rg sqlite3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "pre-merge validation requires: $command" >&2
    exit 1
  }
done

starting_git_status=$(git status --short --untracked-files=all)

while IFS= read -r script; do
  bash -n "$script"
done < <(find scripts tests -type f -name '*.sh' -print | LC_ALL=C sort)

cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings

scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
if [[ -n "$registry_is_set" ]]; then
  scripts/verify-v1-phase5-evidence.sh "${phase5_arguments[@]}"
else
  scripts/verify-v1-phase5-evidence.sh
fi
tests/evals/test-phase5-premerge-trust-forwarding.sh
tests/release/test-v1-phase7-release-proof.sh
tests/release/test-v1-build-receipts.sh
tests/release/test-v1-build-receipt-workflow.sh
tests/release/test-release-workflow-contract.sh

cargo test --workspace --locked

scripts/verify-revision-coherence.sh
tests/coherence/test-revision-coherence.sh
tests/coherence/test-core-state-ownership.sh
tests/core/test-schema-replay-command-contract.sh
tests/bootstrap/test-bootstrap-harness.sh
tests/protocol/smoke-native-artifact.sh target/debug/harness-cli
tests/installer/test-install-harness-modes.sh
tests/installer/assert-consumer-changeset-trackable.sh
tests/maintenance/test-harness-cli-release-classification.sh
tests/maintenance/test-render-changelog-files.sh
tests/docs/test-doc-contracts.sh
tests/evals/test-task-authority.sh
tests/release/test-post-merge-release-recovery.sh

git diff --check

ending_git_status=$(git status --short --untracked-files=all)
if [[ "$ending_git_status" != "$starting_git_status" ]]; then
  printf 'pre-merge validation changed repository status\n' >&2
  printf 'before:\n%s\nafter:\n%s\n' "$starting_git_status" "$ending_git_status" >&2
  fail "validation must preserve the starting repository status"
fi

echo "pre-merge repository contract passed"

#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"

for command in cargo git jq rg sqlite3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "pre-merge validation requires: $command" >&2
    exit 1
  }
done

while IFS= read -r script; do
  bash -n "$script"
done < <(find scripts tests -type f -name '*.sh' -print | LC_ALL=C sort)

cargo fmt --all -- --check
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings

scripts/verify-revision-coherence.sh
tests/coherence/test-revision-coherence.sh
tests/coherence/test-core-state-ownership.sh
tests/core/test-schema-replay-command-contract.sh
tests/changesets/test-automatic-source-capture.sh
tests/boundary/test-phase4-control-plane-freeze.sh
tests/boundary/test-phase5-optional-consumer-split.sh
tests/bootstrap/test-bootstrap-harness.sh
tests/bootstrap/test-core-state-materialization.sh
tests/bootstrap/test-fresh-source-checkout.sh
scripts/verify-core-snapshot.sh
scripts/verify-materialized-core-parity.sh
tests/worktrees/test-core-state-conflict-recovery.sh
tests/snapshot/test-core-snapshot-compaction.sh
tests/ci/test-core-state-rebuild-gate.sh
tests/protocol/smoke-native-artifact.sh target/debug/harness-cli
tests/installer/test-install-harness-modes.sh
tests/installer/assert-consumer-changeset-trackable.sh
tests/maintenance/test-harness-cli-release-classification.sh
tests/maintenance/test-render-changelog-files.sh
tests/docs/test-doc-contracts.sh
tests/workflow/test-repository-workflow.sh
tests/workflow/test-task-authority.sh
tests/release/test-post-merge-release-recovery.sh

git diff --check

echo "pre-merge repository contract passed"

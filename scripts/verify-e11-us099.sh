#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"

[[ ${E11_US099_FORCE_FAILURE:-0} != 1 ]] || {
  echo "intentional US-099 negative verification fixture" >&2
  exit 1
}

cargo metadata --locked --no-deps --format-version 1 |
  jq -e '[.workspace_members[] as $id | .packages[] | select(.id == $id) | .name] == ["harness-cli"]' >/dev/null
cargo fmt -p harness-cli -- --check
cargo clippy -p harness-cli --all-targets --locked -- -D warnings
cargo test -p harness-cli --locked
scripts/validate-changeset-rebuild.sh
scripts/test-validate-changeset-rebuild.sh
tests/core/assert-command-contract.sh
tests/core/assert-schema-replay-command-contract.sh
tests/core/test-schema-replay-command-contract.sh
tests/core/assert-durable-state-boundary.sh
scripts/verify-e11-us098.sh
tests/installer/test-install-harness-modes.sh
tests/installer/assert-agent-authority-contract.sh
tests/installer/assert-install-manifest-links.sh
tests/installer/assert-consumer-changeset-trackable.sh
scripts/test-install-harness-cli-upgrade.sh
tests/maintenance/test-harness-cli-release-classification.sh
tests/maintenance/test-render-changelog-files.sh
tests/release/test-release-workflow-contract.sh
tests/release/test-harness-cli-candidate.sh
(cd docs/stories/epics/E11-symphony-repository-separation/US-099-harness-core-regression-closure/evidence &&
  shasum -a 256 -c regression-summary.json.sha256)

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) candidate_asset=harness-cli-macos-arm64 ;;
  Darwin-x86_64) candidate_asset=harness-cli-macos-x64 ;;
  Linux-aarch64|Linux-arm64) candidate_asset=harness-cli-linux-arm64 ;;
  Linux-x86_64) candidate_asset=harness-cli-linux-x64 ;;
  *) echo "unsupported native candidate-upgrade platform" >&2; exit 1 ;;
esac
upgrade_tmp=$(mktemp -d)
trap 'rm -rf "$upgrade_tmp"' EXIT
initial_url="https://github.com/hoangnb24/repository-harness/releases/download/harness-cli-v0.1.14/$candidate_asset"
curl -fsSL "$initial_url" -o "$upgrade_tmp/initial"
curl -fsSL "$initial_url.sha256" -o "$upgrade_tmp/initial.sha256"
expected_initial=$(awk '{print $1}' "$upgrade_tmp/initial.sha256")
actual_initial=$(shasum -a 256 "$upgrade_tmp/initial" | awk '{print $1}')
[[ "$actual_initial" == "$expected_initial" ]]
chmod 755 "$upgrade_tmp/initial"
tests/installer/test-cli-upgrade-candidate.sh \
  "$upgrade_tmp/initial" target/release/harness-cli "$candidate_asset" \
  harness-cli-v0.0.0-candidate
bash -n scripts/install-harness.sh scripts/build-harness-cli-release.sh
git diff --check

echo "US-099 Harness core regression verification passed"

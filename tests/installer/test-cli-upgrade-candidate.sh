#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
[[ $# == 4 ]] || {
  echo "usage: $0 <initial-artifact> <candidate-artifact> <asset-name> <candidate-ref>" >&2
  exit 2
}
initial=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
candidate=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
asset_name=$3
candidate_ref=$4
[[ "$candidate_ref" =~ ^harness-cli-v[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9]+)*$ ]]
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
target="$temp/consumer"
assets="$temp/assets"
mkdir -p "$target/scripts/bin" "$assets"
cp "$initial" "$target/scripts/bin/harness-cli"
chmod 755 "$target/scripts/bin/harness-cli"
printf 'consumer-owned\n' >"$target/KEEP.txt"
cat >"$target/AGENTS.md" <<'EOF'
# Consumer Agent Rules

Keep this consumer-owned instruction.

<!-- HARNESS:BEGIN -->
stale authority from the initial CLI release
<!-- HARNESS:END -->
EOF
before_keep=$(shasum -a 256 "$target/KEEP.txt" | awk '{print $1}')
before_agents=$(shasum -a 256 "$target/AGENTS.md" | awk '{print $1}')
initial_hash=$(shasum -a 256 "$initial" | awk '{print $1}')
candidate_hash=$(shasum -a 256 "$candidate" | awk '{print $1}')
[[ "$initial_hash" != "$candidate_hash" ]]
candidate_version=$($candidate --version | awk '{print $2}')
if [[ "$candidate_ref" != harness-cli-v0.0.0-candidate ]]; then
  [[ "$candidate_ref" == "harness-cli-v$candidate_version" ]]
fi
"$root/tests/protocol/smoke-v0.1.14-artifact.sh" "$initial"
cp "$candidate" "$assets/$asset_name"
(cd "$assets" && shasum -a 256 "$asset_name" >"$asset_name.sha256")

HARNESS_SOURCE_BASE_URL="file://$root" \
HARNESS_CLI_BASE_URL="file://$assets" \
HARNESS_CLI_PLATFORM="${asset_name#harness-cli-}" \
  "$root/scripts/install-harness.sh" --directory "$target" --merge \
    --upgrade-cli --ref "$candidate_ref" --yes >/dev/null

[[ "$(shasum -a 256 "$target/scripts/bin/harness-cli" | awk '{print $1}')" == "$candidate_hash" ]]
[[ "$(shasum -a 256 "$target/KEEP.txt" | awk '{print $1}')" == "$before_keep" ]]
grep -Fq 'Keep this consumer-owned instruction.' "$target/AGENTS.md"
grep -Fq 'No Harness CLI operation is required.' "$target/AGENTS.md"
! grep -Fq 'stale authority from the initial CLI release' "$target/AGENTS.md"
agent_backup=$(find "$target/.harness-backup" -name AGENTS.md -type f | head -n 1)
[[ "$(shasum -a 256 "$agent_backup" | awk '{print $1}')" == "$before_agents" ]]
[[ -f "$target/scripts/schema/001-init.sql" ]]
"$root/tests/protocol/smoke-native-artifact.sh" "$target/scripts/bin/harness-cli"

echo "checksum-verified upgrade from initial protocol artifact to cleaned candidate passed"
echo "candidate tuple: template_ref=$candidate_ref binary_version=$candidate_version binary_sha256=$candidate_hash"

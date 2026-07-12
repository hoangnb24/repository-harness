#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
installer="$root/scripts/install-harness.sh"
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
platform=fixture-platform
assets="$temp/assets"
mkdir -p "$assets"
printf '%s\n' '#!/usr/bin/env sh' 'exit 0' >"$assets/harness-cli-$platform"
chmod 755 "$assets/harness-cli-$platform"
(cd "$assets" && shasum -a 256 "harness-cli-$platform" >"harness-cli-$platform.sha256")

install() {
  HARNESS_CLI_BASE_URL="file://$assets" \
  HARNESS_CLI_PLATFORM="$platform" \
  HARNESS_CLI_RELEASE_TAG=harness-cli-v0.1.14 \
    "$installer" "$@"
}

# Fresh mode produces the full declared payload, all migrations, ignored local
# DB state, and the platform CLI without initializing an opaque database.
fresh="$temp/fresh"
install --directory "$fresh" --yes >"$temp/fresh.out"
[[ -x "$fresh/scripts/bin/harness-cli" ]]
[[ ! -e "$fresh/harness.db" ]]
[[ "$(find "$fresh/scripts/schema" -type f -name '*.sql' | wc -l | tr -d ' ')" == \
    "$(find "$root/scripts/schema" -type f -name '*.sql' | wc -l | tr -d ' ')" ]]
git -C "$fresh" init -q
git -C "$fresh" check-ignore -q harness.db

# Merge preserves existing project material byte-for-byte while filling gaps.
merge="$temp/merge"
mkdir -p "$merge/docs" "$merge/scripts/custom"
printf 'project agents\n' >"$merge/AGENTS.md"
printf 'project harness doc\n' >"$merge/docs/HARNESS.md"
printf 'custom script\n' >"$merge/scripts/custom/keep.txt"
before_agents=$(shasum -a 256 "$merge/AGENTS.md" | awk '{print $1}')
before_doc=$(shasum -a 256 "$merge/docs/HARNESS.md" | awk '{print $1}')
install --directory "$merge" --merge --yes >"$temp/merge.out"
[[ "$(shasum -a 256 "$merge/AGENTS.md" | awk '{print $1}')" == "$before_agents" ]]
[[ "$(shasum -a 256 "$merge/docs/HARNESS.md" | awk '{print $1}')" == "$before_doc" ]]
grep -Fxq 'custom script' "$merge/scripts/custom/keep.txt"
[[ -f "$merge/docs/ARCHITECTURE.md" && -x "$merge/scripts/bin/harness-cli" ]]

# Override moves every protected tree to one backup before installing cleanly.
override="$temp/override"
mkdir -p "$override/docs" "$override/scripts"
printf 'old agents\n' >"$override/AGENTS.md"
printf 'old docs\n' >"$override/docs/private.md"
printf 'old scripts\n' >"$override/scripts/private.sh"
install --directory "$override" --override --yes >"$temp/override.out"
backup=$(find "$override/.harness-backup" -mindepth 1 -maxdepth 1 -type d | head -n 1)
grep -Fxq 'old agents' "$backup/AGENTS.md"
grep -Fxq 'old docs' "$backup/docs/private.md"
grep -Fxq 'old scripts' "$backup/scripts/private.sh"
[[ ! -e "$override/docs/private.md" && ! -e "$override/scripts/private.sh" ]]
[[ -f "$override/docs/HARNESS.md" && -x "$override/scripts/bin/harness-cli" ]]

# Shim refresh keeps custom instructions, replaces the legacy guide, and backs
# up the exact prior AGENTS.md.
shim="$temp/shim"
mkdir -p "$shim/docs" "$shim/scripts"
cat >"$shim/AGENTS.md" <<'EOF'
# Agent Operating Guide
This repository is in Harness v0. There is no product implementation yet.
## Source Of Truth
legacy
## Task Loop
legacy
## Done Definition
legacy
## Project-specific Instructions
Keep this exact local rule.
EOF
shim_before=$(shasum -a 256 "$shim/AGENTS.md" | awk '{print $1}')
install --directory "$shim" --merge --refresh-agent-shim --yes >"$temp/shim.out"
grep -Fq '<!-- HARNESS:BEGIN -->' "$shim/AGENTS.md"
grep -Fq 'Keep this exact local rule.' "$shim/AGENTS.md"
! grep -Fq '# Agent Operating Guide' "$shim/AGENTS.md"
shim_backup=$(find "$shim/.harness-backup" -name AGENTS.md -type f | head -n 1)
[[ "$(shasum -a 256 "$shim_backup" | awk '{print $1}')" == "$shim_before" ]]

# Dry-run reports the complete intent but creates neither target nor binary.
dry="$temp/dry-run-target"
install --directory "$dry" --dry-run --yes >"$temp/dry.out"
[[ ! -e "$dry" ]]
grep -Fq 'Dry run: no files will be written.' "$temp/dry.out"
grep -Fq 'download harness-cli-fixture-platform -> scripts/bin/harness-cli' "$temp/dry.out"

echo "Bash installer fresh, merge, override, shim-refresh, and dry-run modes passed"

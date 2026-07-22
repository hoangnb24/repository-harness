#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
installer="$root/scripts/install-harness.sh"
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
platform=fixture-platform
assets="$temp/assets"
cargo build --quiet --manifest-path "$root/Cargo.toml" -p harness --locked
harness_core_binary="$root/target/debug/harness"
harness_core_version=$("$harness_core_binary" --version | awk '{ print $NF; exit }')
mkdir -p "$assets"
printf '%s\n' '#!/usr/bin/env sh' 'exit 0' >"$assets/harness-cli-$platform"
chmod 755 "$assets/harness-cli-$platform"
(cd "$assets" && shasum -a 256 "harness-cli-$platform" >"harness-cli-$platform.sha256")
core_source="$temp/core-source"
core_assets="$temp/core-assets"
mkdir -p "$core_source/scripts" "$core_assets"
printf 'harness-v%s\n' "$harness_core_version" >"$core_source/scripts/harness-release-tag"
cp "$harness_core_binary" "$core_assets/harness-fixture-core"
(cd "$core_assets" && shasum -a 256 harness-fixture-core >harness-fixture-core.sha256)

install() {
  HARNESS_CORE_BINARY="$harness_core_binary" \
  HARNESS_CLI_BASE_URL="file://$assets" \
  HARNESS_CLI_PLATFORM="$platform" \
  HARNESS_CLI_RELEASE_TAG=harness-cli-v0.1.14 \
    "$installer" "$@"
}

extract_block() {
  awk '
    /<!-- HARNESS:BEGIN -->/ { in_block = 1 }
    in_block { print }
    /<!-- HARNESS:END -->/ { exit }
  ' "$1"
}

# Fresh default mode produces the small core plus its maintenance CLI. It
# performs no compatibility-CLI, schema, bootstrap, or database-ignore work.
fresh="$temp/fresh"
install --directory "$fresh" --yes >"$temp/fresh.out"
! grep -Fq 'download harness-cli-' "$temp/fresh.out"
grep -Fq 'Harness profile: core' "$temp/fresh.out"
[[ ! -e "$fresh/scripts/bin/harness-cli" ]]
[[ -x "$fresh/scripts/bin/harness" ]]
[[ ! -e "$fresh/scripts/bootstrap-harness.sh" ]]
[[ ! -e "$fresh/scripts/schema" ]]
grep -Fxq 'scripts/bin/harness' "$fresh/.gitignore"
! grep -Fxq 'harness.db' "$fresh/.gitignore"
[[ ! -e "$fresh/harness.db" ]]
[[ -f "$fresh/.harness-core/manifest.json" ]]
cmp -s <(extract_block "$fresh/AGENTS.md") "$root/scripts/agent-harness-block.md"
[[ -f "$fresh/docs/WORKFLOW.md" ]]
[[ -f "$fresh/docs/plans/active/README.md" ]]
[[ -f "$fresh/docs/plans/completed/README.md" ]]
[[ -f "$fresh/docs/templates/exec-plan.md" ]]
grep -Fq 'No control-plane operation is required.' "$fresh/AGENTS.md"
! grep -Fq 'Current Upstream Goal' "$fresh/AGENTS.md"
! grep -Fq 'query matrix --active --summary' "$fresh/AGENTS.md"
for core_file in $(sed -e '/^\s*#/d' -e '/^\s*$/d' "$root/scripts/harness-install-files.txt"); do
  [[ -f "$fresh/$core_file" ]]
done

# Explicit CLI selection adds the complete compatibility bundle, migrations,
# ignore rules, and verified binary without initializing a database.
full="$temp/full"
install --directory "$full" --with-cli --yes >"$temp/full.out"
grep -Fq 'Harness profile: core+cli' "$temp/full.out"
[[ -x "$full/scripts/bin/harness-cli" ]]
[[ -x "$full/scripts/bootstrap-harness.sh" ]]
[[ -f "$full/scripts/bootstrap-harness.ps1" ]]
[[ -f "$full/scripts/harness-cli-release-tag" ]]
[[ -f "$full/docs/contracts/harness-orchestration-v1.md" ]]
[[ "$(find "$full/scripts/schema" -type f -name '*.sql' | wc -l | tr -d ' ')" == \
    "$(find "$root/scripts/schema" -type f -name '*.sql' | wc -l | tr -d ' ')" ]]
git -C "$full" init -q
git -C "$full" check-ignore -q harness.db
[[ ! -e "$full/harness.db" ]]

# Claude generation keeps custom instructions and imports only the canonical
# AGENTS authority instead of restating workflow or compatibility policy.
claude="$temp/claude"
mkdir -p "$claude"
printf '# Local Claude Rules\n\nKeep this Claude-only rule.\n' >"$claude/CLAUDE.md"
install --directory "$claude" --claude --yes >"$temp/claude.out"
grep -Fq 'Keep this Claude-only rule.' "$claude/CLAUDE.md"
cmp -s <(extract_block "$claude/CLAUDE.md") "$root/scripts/claude-harness-block.md"
[[ "$(grep -Fc '@AGENTS.md' "$claude/CLAUDE.md")" == 1 ]]
! grep -Fq '@docs/FEATURE_INTAKE.md' "$claude/CLAUDE.md"
grep -Fq 'No control-plane operation is required.' "$claude/AGENTS.md"

# Merge preserves existing project material byte-for-byte while filling gaps.
merge="$temp/merge"
mkdir -p "$merge/docs" "$merge/scripts/custom" "$merge/scripts/bin"
printf 'project agents\n' >"$merge/AGENTS.md"
printf 'project harness doc\n' >"$merge/docs/HARNESS.md"
printf 'custom script\n' >"$merge/scripts/custom/keep.txt"
printf 'existing cli\n' >"$merge/scripts/bin/harness-cli"
printf 'existing database\n' >"$merge/harness.db"
before_agents=$(shasum -a 256 "$merge/AGENTS.md" | awk '{print $1}')
before_doc=$(shasum -a 256 "$merge/docs/HARNESS.md" | awk '{print $1}')
before_cli=$(shasum -a 256 "$merge/scripts/bin/harness-cli" | awk '{print $1}')
before_db=$(shasum -a 256 "$merge/harness.db" | awk '{print $1}')
install --directory "$merge" --merge --yes >"$temp/merge.out"
[[ "$(shasum -a 256 "$merge/AGENTS.md" | awk '{print $1}')" == "$before_agents" ]]
[[ "$(shasum -a 256 "$merge/docs/HARNESS.md" | awk '{print $1}')" == "$before_doc" ]]
grep -Fxq 'custom script' "$merge/scripts/custom/keep.txt"
[[ "$(shasum -a 256 "$merge/scripts/bin/harness-cli" | awk '{print $1}')" == "$before_cli" ]]
[[ "$(shasum -a 256 "$merge/harness.db" | awk '{print $1}')" == "$before_db" ]]
grep -Fxq 'scripts/bin/harness' "$merge/.gitignore"
! grep -Fxq 'harness.db' "$merge/.gitignore"
[[ -f "$merge/docs/WORKFLOW.md" ]]
[[ ! -e "$merge/docs/ARCHITECTURE.md" ]]

# Core override moves only the paths it owns; an existing scripts tree remains
# untouched when CLI compatibility was not selected.
override="$temp/override"
mkdir -p "$override/docs" "$override/scripts"
printf 'old agents\n' >"$override/AGENTS.md"
printf 'old docs\n' >"$override/docs/private.md"
printf 'old scripts\n' >"$override/scripts/private.sh"
install --directory "$override" --override --yes >"$temp/override.out"
backup=$(find "$override/.harness-backup" -mindepth 1 -maxdepth 1 -type d | head -n 1)
grep -Fxq 'old agents' "$backup/AGENTS.md"
grep -Fxq 'old docs' "$backup/docs/private.md"
[[ ! -e "$override/docs/private.md" ]]
[[ -f "$override/docs/WORKFLOW.md" && ! -e "$override/docs/HARNESS.md" ]]
grep -Fxq 'old scripts' "$override/scripts/private.sh"

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

# CLI upgrades also refresh stale marked authority, without replacing custom
# project text or skipping the normal AGENTS backup.
upgrade="$temp/upgrade"
mkdir -p "$upgrade/docs" "$upgrade/scripts/bin"
cat >"$upgrade/AGENTS.md" <<'EOF'
# Project Agent Rules

Keep this upgrade-local rule.

<!-- HARNESS:BEGIN -->
stale mutation authority
<!-- HARNESS:END -->
EOF
upgrade_before=$(shasum -a 256 "$upgrade/AGENTS.md" | awk '{print $1}')
HARNESS_SOURCE_BASE_URL="file://$root" \
HARNESS_CORE_SOURCE_BASE_URL="file://$core_source" \
HARNESS_CORE_CLI_BASE_URL="file://$core_assets" \
HARNESS_CORE_CLI_PLATFORM=fixture-core \
HARNESS_CLI_BASE_URL="file://$assets" \
HARNESS_CLI_PLATFORM="$platform" \
  "$installer" --directory "$upgrade" --merge --upgrade-cli \
    --ref harness-cli-v0.1.14 --yes >"$temp/upgrade.out"
grep -Fq 'Keep this upgrade-local rule.' "$upgrade/AGENTS.md"
! grep -Fq 'stale mutation authority' "$upgrade/AGENTS.md"
cmp -s <(extract_block "$upgrade/AGENTS.md") "$root/scripts/agent-harness-block.md"
upgrade_backup=$(find "$upgrade/.harness-backup" -name AGENTS.md -type f | head -n 1)
[[ "$(shasum -a 256 "$upgrade_backup" | awk '{print $1}')" == "$upgrade_before" ]]

# Malformed or duplicate authority markers fail closed instead of appending a
# second policy block that leaves precedence ambiguous.
malformed="$temp/malformed"
mkdir -p "$malformed/docs" "$malformed/scripts"
printf 'custom\n<!-- HARNESS:BEGIN -->\nstale without end\n' >"$malformed/AGENTS.md"
if install --directory "$malformed" --merge --refresh-agent-shim --yes \
  >"$temp/malformed.out" 2>&1; then
  echo "installer unexpectedly accepted malformed Harness markers" >&2
  exit 1
fi
grep -Fq 'exactly one complete Harness marker pair' "$temp/malformed.out"

# Dry-run reports the complete intent but creates neither target nor binary.
dry="$temp/dry-run-target"
HARNESS_CLI_BASE_URL="file://$temp/does-not-exist" \
  install --directory "$dry" --dry-run --yes >"$temp/dry.out"
[[ ! -e "$dry" ]]
grep -Fq 'Dry run: no files will be written.' "$temp/dry.out"
grep -Fq 'Harness profile: core' "$temp/dry.out"
! grep -Fq 'download harness-cli-fixture-platform -> scripts/bin/harness-cli' "$temp/dry.out"
! grep -Fq '.gitignore (append harness rules)' "$temp/dry.out"

cli_dry="$temp/cli-dry-run-target"
install --directory "$cli_dry" --with-cli --dry-run --yes >"$temp/cli-dry.out"
[[ ! -e "$cli_dry" ]]
grep -Fq 'Harness profile: core+cli' "$temp/cli-dry.out"
grep -Fq 'download harness-cli-fixture-platform -> scripts/bin/harness-cli' "$temp/cli-dry.out"
grep -Fq '.gitignore (append harness rules)' "$temp/cli-dry.out"

# A bad candidate is rejected before any compatibility member reaches the
# target. The already-installed core remains usable.
bad_assets="$temp/bad-assets"
mkdir -p "$bad_assets"
cp "$assets/harness-cli-$platform" "$bad_assets/harness-cli-$platform"
printf 'bad-checksum\n' >"$bad_assets/harness-cli-$platform.sha256"
failed="$temp/failed-cli"
if HARNESS_CORE_BINARY="$harness_core_binary" \
  HARNESS_CLI_BASE_URL="file://$bad_assets" HARNESS_CLI_PLATFORM="$platform" \
  "$installer" --directory "$failed" --with-cli --yes >"$temp/failed-cli.out" 2>&1; then
  echo "installer unexpectedly accepted a bad CLI checksum" >&2
  exit 1
fi
[[ -f "$failed/AGENTS.md" && -f "$failed/docs/WORKFLOW.md" ]]
[[ -x "$failed/scripts/bin/harness" ]]
[[ ! -e "$failed/docs/FEATURE_INTAKE.md" ]]
[[ ! -e "$failed/scripts/bootstrap-harness.sh" ]]
[[ ! -e "$failed/scripts/bin/harness-cli" ]]
grep -Fxq 'scripts/bin/harness' "$failed/.gitignore"
! grep -Fxq 'harness.db' "$failed/.gitignore"

# A core conflict retains the candidate without replacing the installed binary.
# After the resolution is edited, rerunning the installer automatically invokes
# the same candidate with --continue and replaces the binary only after success.
conflict="$temp/core-conflict"
fake_candidate="$temp/fake-harness-candidate"
mkdir -p "$conflict/.harness-core" "$conflict/scripts/bin"
printf '{"schema_version":1,"core_version":"0.1.3","files":[]}\n' \
  >"$conflict/.harness-core/manifest.json"
printf 'old executable\n' >"$conflict/scripts/bin/harness"
chmod 755 "$conflict/scripts/bin/harness"
old_binary_hash=$(shasum -a 256 "$conflict/scripts/bin/harness" | awk '{ print $1 }')
cat >"$fake_candidate" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  echo "harness 0.1.4"
  exit 0
fi
target=""
continuing=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --directory) target=$2; shift 2 ;;
    --continue) continuing=1; shift ;;
    *) shift ;;
  esac
done
if [ "$continuing" -eq 1 ]; then
  cp "$target/.harness-core/update/resolved/AGENTS.md" "$target/AGENTS.md"
  rm -rf "$target/.harness-core/update"
  exit 0
fi
mkdir -p "$target/.harness-core/update/resolved"
printf 'resolved content required\n' >"$target/.harness-core/update/resolved/AGENTS.md"
printf '{"schema_version":2,"from_version":"0.1.3","to_version":"0.1.4","conflicts":[],"frozen_files":[]}\n' \
  >"$target/.harness-core/update/session.json"
exit 2
EOF
chmod 755 "$fake_candidate"
if HARNESS_CORE_BINARY="$fake_candidate" \
  "$installer" --directory "$conflict" --merge --yes >"$temp/core-conflict.out" 2>&1; then
  echo "installer unexpectedly reported a conflicted core update as successful" >&2
  exit 1
fi
[[ "$(shasum -a 256 "$conflict/scripts/bin/harness" | awk '{ print $1 }')" == "$old_binary_hash" ]]
[[ -x "$conflict/.harness-core/update-candidate/harness" ]]
printf 'human-approved result\n' >"$conflict/.harness-core/update/resolved/AGENTS.md"
HARNESS_CORE_BINARY="$fake_candidate" \
  "$installer" --directory "$conflict" --merge --yes >"$temp/core-continue.out"
grep -Fxq 'human-approved result' "$conflict/AGENTS.md"
cmp -s "$fake_candidate" "$conflict/scripts/bin/harness"
[[ ! -e "$conflict/.harness-core/update" ]]
[[ ! -e "$conflict/.harness-core/update-candidate" ]]

echo "Bash core/CLI profiles, merge, override, shims, upgrade, rollback, and dry-run modes passed"

#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
cli="$root/target/debug/harness-cli"

cargo build --quiet --manifest-path "$root/Cargo.toml" -p harness-cli --locked

fresh="$temp/fresh.db"
HARNESS_CLI="$cli" HARNESS_DB_PATH="$fresh" "$root/scripts/bootstrap-harness.sh" >"$temp/fresh.out"
grep -Fq 'Harness ready:' "$temp/fresh.out"
[[ "$(sqlite3 "$fresh" 'SELECT MAX(version) FROM schema_version;')" == 14 ]]

old="$temp/old.db"
sqlite3 "$old" <"$root/scripts/schema/001-init.sql" >/dev/null
HARNESS_CLI="$cli" HARNESS_DB_PATH="$old" "$root/scripts/bootstrap-harness.sh" >"$temp/old.out"
[[ "$(sqlite3 "$old" 'SELECT MAX(version) FROM schema_version;')" == 14 ]]

HARNESS_CLI="$cli" HARNESS_DB_PATH="$fresh" "$root/scripts/bootstrap-harness.sh" >"$temp/current.out"
grep -Fq 'Harness ready:' "$temp/current.out"

unsupported="$temp/unsupported.db"
sqlite3 "$unsupported" 'CREATE TABLE schema_version(version INTEGER PRIMARY KEY); INSERT INTO schema_version VALUES(999);'
if HARNESS_CLI="$cli" HARNESS_DB_PATH="$unsupported" "$root/scripts/bootstrap-harness.sh" \
  >"$temp/unsupported.out" 2>&1; then
  echo "bootstrap unexpectedly accepted an unsupported schema" >&2
  exit 1
fi
grep -Fq "database schema is outside the CLI's supported range" "$temp/unsupported.out"

consumer="$temp/consumer"
mkdir -p "$consumer/scripts/bin" "$consumer/scripts/schema"
cp "$root/scripts/bootstrap-harness.sh" "$consumer/scripts/bootstrap-harness.sh"
cp "$root/scripts/harness-cli-release-tag" "$consumer/scripts/harness-cli-release-tag"
cp "$root/scripts/schema/"*.sql "$consumer/scripts/schema/"
cp "$cli" "$consumer/scripts/bin/harness-cli"
chmod 755 "$consumer/scripts/bootstrap-harness.sh" "$consumer/scripts/bin/harness-cli"
"$consumer/scripts/bootstrap-harness.sh" >"$temp/consumer.out"
grep -Fq 'Harness ready:' "$temp/consumer.out"
[[ "$(sqlite3 "$consumer/harness.db" 'SELECT MAX(version) FROM schema_version;')" == 14 ]]

printf 'harness-cli-v9.9.9\n' >"$consumer/scripts/harness-cli-release-tag"
if "$consumer/scripts/bootstrap-harness.sh" >"$temp/version.out" 2>&1; then
  echo "bootstrap unexpectedly accepted a CLI/pin mismatch" >&2
  exit 1
fi
grep -Fq 'does not match pinned release harness-cli-v9.9.9' "$temp/version.out"

missing_source="$temp/missing-source"
mkdir -p "$missing_source/scripts" "$missing_source/crates/harness-cli"
cp "$root/scripts/bootstrap-harness.sh" "$missing_source/scripts/bootstrap-harness.sh"
touch "$missing_source/Cargo.toml" "$missing_source/crates/harness-cli/Cargo.toml"
if "$missing_source/scripts/bootstrap-harness.sh" >"$temp/missing-source.out" 2>&1; then
  echo "bootstrap unexpectedly initialized empty source-repository state" >&2
  exit 1
fi
grep -Fq 'tracked verified core state is missing' \
  "$temp/missing-source.out"

grep -Fq '"needs_migration"' "$root/scripts/bootstrap-harness.ps1"
grep -Fq '"unsupported"' "$root/scripts/bootstrap-harness.ps1"
grep -Fq 'ConvertFrom-Json' "$root/scripts/bootstrap-harness.ps1"
grep -Fq 'materialize-core-state.ps1' "$root/scripts/bootstrap-harness.ps1"

echo "source isolation, consumer init, migration, refusal, version, and PowerShell bootstrap contracts passed"

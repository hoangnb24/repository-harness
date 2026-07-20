#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cli="$root/target/debug/harness-cli"
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
tuple_hash() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" "$2"
  else
    shasum -a 256 "$1" "$2"
  fi
}
state_root="$temp/state"
directory="$state_root/.harness/core-state"
mkdir -p "$state_root/.harness/changesets"
cp "$root/.harness/changesets/"*.changeset.jsonl "$state_root/.harness/changesets/"

HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$root/harness.db" \
  "$cli" db snapshot --output "$temp/source.db" --json >/dev/null
HARNESS_CLI="$cli" HARNESS_SOURCE_DB="$temp/source.db" HARNESS_CORE_STATE_DIR="$directory" \
  "$root/scripts/publish-core-snapshot.sh" >/dev/null
old_logical=$(jq -r '.snapshot.logical_sha256' "$directory/manifest.json")

sqlite3 "$temp/source.db" "UPDATE story SET notes='snapshot replacement fixture' WHERE id='US-118';"
HARNESS_CLI="$cli" HARNESS_SOURCE_DB="$temp/source.db" HARNESS_CORE_STATE_DIR="$directory" \
  "$root/scripts/publish-core-snapshot.sh" --replace --expected-logical-sha "$old_logical" >/dev/null
new_logical=$(jq -r '.snapshot.logical_sha256' "$directory/manifest.json")
[[ "$new_logical" != "$old_logical" ]]
HARNESS_CLI="$cli" HARNESS_CORE_MANIFEST="$directory/manifest.json" \
  HARNESS_CORE_SNAPSHOT="$directory/harness.db" "$root/scripts/verify-core-snapshot.sh" >/dev/null
[[ $(sqlite3 "$directory/harness.db" 'PRAGMA journal_mode;') == delete ]]
[[ ! -e "$directory/harness.db-wal" && ! -e "$directory/harness.db-shm" ]]

tuple_before=$(tuple_hash "$directory/harness.db" "$directory/manifest.json")
if HARNESS_CLI="$cli" HARNESS_SOURCE_DB="$temp/source.db" HARNESS_CORE_STATE_DIR="$directory" \
  "$root/scripts/publish-core-snapshot.sh" --replace \
  --expected-logical-sha aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  >"$temp/stale.out" 2>&1; then
  echo "snapshot replacement unexpectedly ignored a stale precondition" >&2
  exit 1
fi
grep -Fq 'replacement precondition' "$temp/stale.out"
[[ $(tuple_hash "$directory/harness.db" "$directory/manifest.json") == "$tuple_before" ]]

HARNESS_CLI="$cli" HARNESS_CORE_STATE_ROOT="$state_root" HARNESS_DB_PATH="$temp/materialized.db" \
  "$root/scripts/materialize-core-state.sh" >/dev/null
[[ $(sqlite3 "$temp/materialized.db" "SELECT notes FROM story WHERE id='US-118';") == 'snapshot replacement fixture' ]]

echo "snapshot replacement verifies old and new tuples, enforces compare-and-swap, and materializes the compacted state"

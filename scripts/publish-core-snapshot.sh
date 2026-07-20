#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cli=${HARNESS_CLI:-$root/scripts/bin/harness-cli}
source_db=${HARNESS_SOURCE_DB:-$root/harness.db}
directory=${HARNESS_CORE_STATE_DIR:-$root/.harness/core-state}
snapshot="$directory/harness.db"
manifest="$directory/manifest.json"
replace=0
expected_logical_sha=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --replace) replace=1; shift ;;
    --expected-logical-sha)
      [[ $# -ge 2 ]] || { echo "--expected-logical-sha requires a value" >&2; exit 2; }
      expected_logical_sha=$2
      shift 2
      ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

fail() { printf 'Core snapshot publication failed: %s\n' "$*" >&2; exit 1; }
[[ -f "$source_db" ]] || fail "source database is missing: $source_db"
for command in jq sqlite3; do command -v "$command" >/dev/null 2>&1 || fail "$command is required"; done

if [[ -e "$snapshot" || -e "$manifest" ]]; then
  [[ -f "$snapshot" && -f "$manifest" ]] || fail "existing snapshot tuple is incomplete"
  [[ $replace == 1 ]] || fail "published tuple already exists; use the reviewed --replace procedure"
  [[ "$expected_logical_sha" =~ ^[0-9a-f]{64}$ ]] || fail "replacement requires --expected-logical-sha <current-manifest-hash>"
  [[ $(jq -r '.snapshot.logical_sha256' "$manifest") == "$expected_logical_sha" ]] ||
    fail "current manifest logical hash differs from the replacement precondition"
  HARNESS_CORE_MANIFEST="$manifest" HARNESS_CORE_SNAPSHOT="$snapshot" HARNESS_CLI="$cli" \
    "$root/scripts/verify-core-snapshot.sh" >/dev/null || fail "existing tuple is not verified"
else
  [[ $replace == 0 ]] || fail "--replace requires an existing verified tuple"
fi

HARNESS_CLI="$cli" HARNESS_SOURCE_DB="$source_db" \
  "$root/scripts/verify-core-state-ownership.sh" >/dev/null || fail "source database violates core ownership"

mkdir -p "$directory"
temp=$(mktemp -d "$directory/.publish.XXXXXX")
activated=0
cleanup() {
  if [[ $activated == 0 && -f "$temp/previous-harness.db" && -f "$temp/previous-manifest.json" ]]; then
    rm -f "$snapshot" "$manifest"
    mv "$temp/previous-harness.db" "$snapshot"
    mv "$temp/previous-manifest.json" "$manifest"
  elif [[ $activated == 0 && $replace == 0 ]]; then
    rm -f "$snapshot" "$manifest"
  fi
  rm -rf "$temp"
}
trap cleanup EXIT

snapshot_json=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$source_db" \
  "$cli" db snapshot --output "$temp/harness.db" --json)
: >"$temp/included.jsonl"
while IFS= read -r file; do
  relative=${file#"$root/"}
  status=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$source_db" \
    "$cli" db changeset status "$file" --json)
  jq -cn --arg id "$(jq -r '.result.id' <<<"$status")" \
    --arg path "$relative" --arg sha "$(jq -r '.result.content_sha256' <<<"$status")" \
    '{id:$id,path:$path,content_sha256:$sha}' >>"$temp/included.jsonl"
done < <(find "$root/.harness/changesets" -maxdepth 1 -type f -name '*.changeset.jsonl' -print | LC_ALL=C sort)

schema=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$source_db" \
  "$cli" query contract --json | jq -r '.result.database_schema_version')
jq -n \
  --arg file_sha "$(jq -r '.result.snapshot_file_sha256' <<<"$snapshot_json")" \
  --arg logical_sha "$(jq -r '.result.source_logical_sha256' <<<"$snapshot_json")" \
  --argjson schema "$schema" \
  --slurpfile included "$temp/included.jsonl" \
  '{format_version:1,snapshot:{path:".harness/core-state/harness.db",file_sha256:$file_sha,logical_sha256:$logical_sha,schema_version:$schema},included_changesets:$included}' \
  >"$temp/manifest.json"

chmod a-w "$temp/harness.db"
HARNESS_CORE_MANIFEST="$temp/manifest.json" HARNESS_CORE_SNAPSHOT="$temp/harness.db" HARNESS_CLI="$cli" \
  "$root/scripts/verify-core-snapshot.sh" >/dev/null

if [[ $replace == 1 ]]; then
  mv "$snapshot" "$temp/previous-harness.db"
  mv "$manifest" "$temp/previous-manifest.json"
fi
rm -f "$snapshot-wal" "$snapshot-shm"
mv "$temp/harness.db" "$snapshot"
mv "$temp/manifest.json" "$manifest"
HARNESS_CORE_MANIFEST="$manifest" HARNESS_CORE_SNAPSHOT="$snapshot" HARNESS_CLI="$cli" \
  "$root/scripts/verify-core-snapshot.sh" >/dev/null
activated=1
echo "Published verified core snapshot: $snapshot"

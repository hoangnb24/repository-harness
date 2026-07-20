#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cli=${HARNESS_CLI:-$root/scripts/bin/harness-cli}
manifest=${HARNESS_CORE_MANIFEST:-$root/.harness/core-state/manifest.json}
snapshot=${HARNESS_CORE_SNAPSHOT:-$root/.harness/core-state/harness.db}

fail() { printf 'Core snapshot verification failed: %s\n' "$*" >&2; exit 1; }
sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
  else fail "sha256sum or shasum is required"; fi
}

for command in jq sqlite3; do command -v "$command" >/dev/null 2>&1 || fail "$command is required"; done
for file in "$cli" "$manifest" "$snapshot"; do [[ -e "$file" ]] || fail "missing input: $file"; done
[[ ! -e "$snapshot-wal" && ! -e "$snapshot-shm" ]] || fail "tracked snapshot has SQLite sidecars"
[[ $(sqlite3 "$snapshot" 'PRAGMA journal_mode;') == delete ]] || fail "tracked snapshot journal mode is not DELETE"

expected_file=$(jq -er '.snapshot.file_sha256' "$manifest") || fail "manifest snapshot hash is missing"
actual_file=$(sha256_file "$snapshot")
[[ "$actual_file" == "$expected_file" ]] || fail "snapshot byte hash differs from manifest"

temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
probe=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$snapshot" \
  "$cli" db snapshot --output "$temp/probe.db" --json) || fail "SQLite snapshot verification failed"
expected_logical=$(jq -er '.snapshot.logical_sha256' "$manifest")
actual_logical=$(jq -r '.result.source_logical_sha256' <<<"$probe")
[[ "$actual_logical" == "$expected_logical" ]] || fail "snapshot logical hash differs from manifest"

contract=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$snapshot" "$cli" query contract --json)
[[ $(jq -r '.result.database_state' <<<"$contract") == current ]] || fail "snapshot schema is not current"
[[ $(jq -r '.result.database_schema_version' <<<"$contract") == \
   $(jq -r '.snapshot.schema_version' "$manifest") ]] || fail "snapshot schema differs from manifest"

HARNESS_CLI="$cli" HARNESS_SOURCE_DB="$snapshot" \
  "$root/scripts/verify-core-state-ownership.sh" >/dev/null || fail "snapshot violates core ownership"

sqlite3 "$snapshot" .dump >"$temp/dump.sql"
if grep -Fq "$root" "$temp/dump.sql"; then fail "snapshot contains the source checkout absolute path"; fi
if grep -Eiq -- '-----BEGIN ([A-Z ]+ )?PRIVATE KEY-----|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer[[:space:]]+[A-Za-z0-9._-]{20,}' "$temp/dump.sql"; then
  fail "snapshot contains private-key or token-shaped material"
fi

while IFS=$'\t' read -r id path sha; do
  [[ -n "$id" ]] || continue
  file="$root/$path"
  [[ -f "$file" ]] || fail "included changeset is missing: $path"
  status=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$snapshot" \
    "$cli" db changeset status "$file" --json)
  [[ $(jq -r '.result.id' <<<"$status") == "$id" && \
     $(jq -r '.result.content_sha256' <<<"$status") == "$sha" ]] ||
    fail "included changeset identity differs: $path"
done < <(jq -r '.included_changesets[] | [.id,.path,.content_sha256] | @tsv' "$manifest")

echo "verified core snapshot: schema=$(jq -r '.snapshot.schema_version' "$manifest") logical_sha256=$actual_logical"

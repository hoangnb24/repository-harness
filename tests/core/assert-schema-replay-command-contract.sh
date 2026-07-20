#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
cli=${HARNESS_CLI:-$root/target/debug/harness-cli}
schema_dir=${HARNESS_SCHEMA_DIR:-$root/scripts/schema}
manifest=${HARNESS_COMMAND_MANIFEST:-$root/tests/core/harness-command-contract.txt}
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT

for command in sqlite3 jq rg; do command -v "$command" >/dev/null || { echo "missing command: $command" >&2; exit 1; }; done
test -x "$cli" || { echo "Harness CLI is not executable: $cli" >&2; exit 1; }
test -f "$manifest" || { echo "command manifest is missing: $manifest" >&2; exit 1; }

schema_files=()
while IFS= read -r file; do schema_files+=("$file"); done < <(find "$schema_dir" -maxdepth 1 -type f -name '*.sql' | LC_ALL=C sort)
current=${#schema_files[@]}
test "$current" -gt 0
test "$(basename "${schema_files[0]}")" = 001-init.sql
for ((index=0; index<current; index++)); do
  printf -v expected_prefix '%03d-' "$((index + 1))"
  case "$(basename "${schema_files[$index]}")" in
    "$expected_prefix"*) ;;
    *) echo "schema migration sequence is not contiguous at $((index + 1))" >&2; exit 1;;
  esac
done

fresh="$temp/fresh.db"
HARNESS_DB_PATH="$fresh" "$cli" init >/dev/null
test "$(sqlite3 "$fresh" 'SELECT MAX(version) FROM schema_version;')" -eq "$current"
test "$(sqlite3 "$fresh" 'PRAGMA integrity_check;')" = ok
test "$(sqlite3 "$fresh" 'PRAGMA foreign_key_check;')" = ""

for ((old=1; old<current; old++)); do
  db="$temp/v$old.db"
  for ((index=0; index<old; index++)); do sqlite3 "$db" <"${schema_files[$index]}" >/dev/null; done
  test "$(sqlite3 "$db" 'SELECT MAX(version) FROM schema_version;')" -eq "$old"
  HARNESS_DB_PATH="$db" "$cli" migrate >/dev/null
  test "$(sqlite3 "$db" 'SELECT MAX(version) FROM schema_version;')" -eq "$current"
  test "$(sqlite3 "$db" 'SELECT COUNT(*) FROM schema_version;')" -eq "$current"
  test "$(sqlite3 "$db" 'PRAGMA integrity_check;')" = ok
  test "$(sqlite3 "$db" 'PRAGMA foreign_key_check;')" = ""
done

while IFS= read -r path; do
  [[ -n "$path" && "$path" != \#* ]] || continue
  read -r -a parts <<<"$path"
  output=$("$cli" "${parts[@]}" --help 2>&1) || { echo "public command disappeared: $path" >&2; exit 1; }
  grep -Fq 'Usage:' <<<"$output" || { echo "public command has no help contract: $path" >&2; exit 1; }
done <"$manifest"

"$root/scripts/validate-changeset-rebuild.sh" >/dev/null
"$root/scripts/test-validate-changeset-rebuild.sh" >/dev/null
if rg -n -i 'symphony|US-[0-9]' \
  "$root/scripts/validate-changeset-rebuild.sh" \
  "$root/scripts/test-validate-changeset-rebuild.sh" \
  "$root/tests/fixtures/changesets/generic-rebuild" >"$temp/product-refs"; then
  echo "generic replay proof contains product-owned IDs or names" >&2
  cat "$temp/product-refs" >&2
  exit 1
fi

contract=$(HARNESS_DB_PATH="$fresh" "$cli" query contract --json)
jq -e --argjson current "$current" '
  .result.protocol_version == 1 and
  .result.schema_minimum == 1 and
  .result.schema_maximum == $current and
  .result.database_schema_version == $current and
  .result.database_state == "current" and
  (["changesets.apply.v1","changesets.status-sha.v1","entity-revision-conflicts.v1","isolated-db-snapshot.v1",
    "semantic-operation-log.v1","stories.read.v1","stories.write.v1",
    "story-dependencies.read-write.v1","story-hierarchy.read-write.v1",
    "work-graph.read.v1"] - .result.capabilities | length == 0)
' <<<"$contract" >/dev/null

echo "schema 001-$current, generic replay, protocol, and public command surface passed"

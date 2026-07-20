#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cli=${HARNESS_CLI:-$root/scripts/bin/harness-cli}
source_db=${HARNESS_SOURCE_DB:-$root/harness.db}
[[ -f "$source_db" ]] || { echo "materialized parity source is missing: $source_db" >&2; exit 1; }

temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
rebuilt="$temp/harness.db"
HARNESS_CLI="$cli" HARNESS_DB_PATH="$rebuilt" "$root/scripts/materialize-core-state.sh" >/dev/null

source_tables=$(sqlite3 "$source_db" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
rebuilt_tables=$(sqlite3 "$rebuilt" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
[[ "$source_tables" == "$rebuilt_tables" ]] || { echo "materialized table set differs from source" >&2; exit 1; }

while IFS= read -r table; do
  [[ -n "$table" && "$table" != changeset_applied ]] || continue
  escaped=${table//\"/\"\"}
  difference=$(sqlite3 "$source_db" "
    ATTACH DATABASE '$rebuilt' AS rebuilt;
    SELECT
      (SELECT count(*) FROM (SELECT * FROM main.\"$escaped\" EXCEPT SELECT * FROM rebuilt.\"$escaped\")) +
      (SELECT count(*) FROM (SELECT * FROM rebuilt.\"$escaped\" EXCEPT SELECT * FROM main.\"$escaped\"));
  ")
  [[ "$difference" == 0 ]] || { echo "materialized durable rows differ in table: $table" >&2; exit 1; }
done <<<"$source_tables"

echo "materialized core matches source across all durable tables; changeset_applied is epoch-derived"

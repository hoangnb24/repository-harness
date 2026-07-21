#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
cli="$root/target/debug/harness-cli"
fixture="$temp/repository"
db="$fixture/harness.db"
mkdir -p "$fixture/scripts"
cp -R "$root/scripts/schema" "$fixture/scripts/schema"
printf 'repository sentinel\n' >"$fixture/SENTINEL.txt"

cargo build --quiet --manifest-path "$root/Cargo.toml" -p harness-cli --locked

run() {
  HARNESS_REPO_ROOT="$fixture" HARNESS_DB_PATH="$db" "$cli" "$@"
}

run_logged() {
  local run_id=$1
  shift
  HARNESS_REPO_ROOT="$fixture" HARNESS_DB_PATH="$db" HARNESS_RUN_ID="$run_id" \
    "$cli" "$@"
}

logical_hash() {
  sqlite3 "$db" '.dump' | shasum -a 256 | awk '{print $1}'
}

state_fingerprint() {
  local changeset_hash=absent
  if [[ -d "$fixture/.harness/changesets" ]]; then
    changeset_hash=$(find "$fixture/.harness/changesets" -type f -name '*.changeset.jsonl' -print |
      LC_ALL=C sort | shasum -a 256 | awk '{print $1}')
  fi
  printf '%s|%s|%s|%s|%s\n' \
    "$(logical_hash)" \
    "$(sqlite3 "$db" 'SELECT count(*) FROM intake;')" \
    "$(sqlite3 "$db" 'SELECT count(*) FROM trace;')" \
    "$(shasum -a 256 "$fixture/SENTINEL.txt" | awk '{print $1}')" \
    "$changeset_hash"
}

# Missing-state diagnosis is discovery only: it reports the missing database
# without creating the file it was asked to inspect.
missing="$temp/missing.db"
HARNESS_REPO_ROOT="$fixture" HARNESS_DB_PATH="$missing" "$cli" query contract --json \
  >"$temp/missing-contract.json"
jq -e '.result.database_state == "missing" and .result.database_schema_version == null' \
  "$temp/missing-contract.json" >/dev/null
[[ ! -e "$missing" ]]

run init >/dev/null
for story in READ FAIL CHANGE; do
  run story add --id "US-$story" --title "$story task" --lane normal --verify true >/dev/null
done

# Review/diagnose/status operations may inspect broad state, but they must not
# alter logical DB content, intake/trace counts, repository files, or semantic
# operation logs.
before_read_only=$(state_fingerprint)
run query matrix --active --summary >"$temp/matrix.txt"
run query stories --json >"$temp/stories.json"
run query sql 'WITH active AS (SELECT id FROM story WHERE status="planned") SELECT count(*) FROM active;' \
  >"$temp/select.txt"
run audit >"$temp/audit.txt"
run propose >"$temp/propose.txt"
run query tools --capability optional-provider --status present --json >"$temp/tools.json"
after_read_only=$(state_fingerprint)
[[ "$before_read_only" == "$after_read_only" ]]
grep -Fq 'US-READ' "$temp/matrix.txt"
jq -e '.result.stories | length == 3' "$temp/stories.json" >/dev/null
jq -e 'length == 0' "$temp/tools.json" >/dev/null
[[ ! -d "$fixture/.harness/changesets" ]]

# A disguised write through the query surface is denied and leaves the same
# complete state fingerprint.
before_sql_denial=$(state_fingerprint)
if run query sql 'PRAGMA user_version=999;' >"$temp/sql-write.out" 2>"$temp/sql-write.err"; then
  echo "task eval: query sql unexpectedly accepted a mutating PRAGMA" >&2
  exit 1
fi
grep -Fq 'query sql is read-only' "$temp/sql-write.err"
[[ "$(state_fingerprint)" == "$before_sql_denial" ]]

# Completion without the active-state prerequisite is rejected before proof or
# semantic logging, so a failed implementation attempt has no side effects.
before_failed_completion=$(state_fingerprint)
if run_logged eval_failed story complete US-FAIL >"$temp/failed.out" 2>"$temp/failed.err"; then
  echo "task eval: planned story unexpectedly completed" >&2
  exit 1
fi
grep -Fq 'move it to in_progress or changed before completion' "$temp/failed.err"
[[ "$(state_fingerprint)" == "$before_failed_completion" ]]
[[ ! -e "$fixture/.harness/changesets/eval_failed.changeset.jsonl" ]]

# An explicitly authorized change has the opposite oracle: it must produce the
# requested state transition, fresh passing proof, and exactly the expected
# semantic operations.
run_logged eval_change story update --id US-CHANGE --status in_progress >/dev/null
run_logged eval_change story complete US-CHANGE >/dev/null
[[ "$(sqlite3 "$db" "SELECT status FROM story WHERE id='US-CHANGE';")" == implemented ]]
[[ "$(sqlite3 "$db" "SELECT last_verified_result FROM story WHERE id='US-CHANGE';")" == pass ]]
changeset="$fixture/.harness/changesets/eval_change.changeset.jsonl"
[[ -f "$changeset" ]]
jq -s -e 'map(.op) == ["changeset.header", "story.update", "story.complete"]' \
  "$changeset" >/dev/null
[[ "$(sqlite3 "$db" "SELECT status FROM story WHERE id='US-FAIL';")" == planned ]]
[[ "$(sqlite3 "$db" 'SELECT count(*) FROM intake;')" == 0 ]]
[[ "$(sqlite3 "$db" 'SELECT count(*) FROM trace;')" == 0 ]]

echo "representative read-only, denied, missing-tool, failed-proof, and authorized-change task effects passed"

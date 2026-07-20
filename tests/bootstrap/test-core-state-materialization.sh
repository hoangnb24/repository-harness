#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cli="$root/target/debug/harness-cli"
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
state="$temp/state"
mkdir -p "$state/.harness/core-state" "$state/.harness/changesets" "$state/scripts/schema"
cp "$root/scripts/schema/"*.sql "$state/scripts/schema/"

cargo build --quiet --manifest-path "$root/Cargo.toml" -p harness-cli --locked
HARNESS_REPO_ROOT="$state" HARNESS_DB_PATH="$temp/source.db" "$cli" init >/dev/null

cat >"$state/.harness/changesets/included.changeset.jsonl" <<'JSONL'
{"op":"changeset.header","version":1,"run_id":"run_fixture_included","base_schema_version":14}
{"op":"story.add","version":1,"id":"US-093","payload":{"title":"Receipt 93","risk_lane":"normal","status":"implemented"}}
{"op":"story.add","version":1,"id":"US-094","payload":{"title":"Receipt 94","risk_lane":"normal","status":"implemented"}}
{"op":"story.add","version":1,"id":"US-095","payload":{"title":"Receipt 95","risk_lane":"normal","status":"implemented"}}
{"op":"story.add","version":1,"id":"US-096","payload":{"title":"Receipt 96","risk_lane":"normal","status":"implemented"}}
{"op":"story.add","version":1,"id":"CORE-BASE","payload":{"title":"Baseline state","risk_lane":"normal","status":"implemented"}}
{"op":"story.update","version":1,"id":"US-093","payload":{"status":"implemented"}}
{"op":"story.update","version":1,"id":"US-094","payload":{"status":"implemented"}}
{"op":"story.update","version":1,"id":"US-095","payload":{"status":"implemented"}}
{"op":"story.update","version":1,"id":"US-096","payload":{"status":"implemented"}}
{"op":"story.update","version":1,"id":"CORE-BASE","payload":{"status":"implemented"}}
JSONL
cat >"$state/.harness/changesets/later.changeset.jsonl" <<'JSONL'
{"op":"changeset.header","version":1,"run_id":"run_fixture_later","base_schema_version":14}
{"op":"story.add","version":1,"id":"CORE-LATER","payload":{"title":"Post snapshot state","risk_lane":"normal","status":"planned"}}
JSONL

HARNESS_REPO_ROOT="$state" HARNESS_DB_PATH="$temp/source.db" \
  "$cli" db changeset apply "$state/.harness/changesets/included.changeset.jsonl" --json >/dev/null
snapshot_json=$(HARNESS_REPO_ROOT="$state" HARNESS_DB_PATH="$temp/source.db" \
  "$cli" db snapshot --output "$state/.harness/core-state/harness.db" --json)
included_status=$(HARNESS_REPO_ROOT="$state" HARNESS_DB_PATH="$temp/source.db" \
  "$cli" db changeset status "$state/.harness/changesets/included.changeset.jsonl" --json)
jq -n \
  --arg file_sha "$(jq -r '.result.snapshot_file_sha256' <<<"$snapshot_json")" \
  --arg logical_sha "$(jq -r '.result.source_logical_sha256' <<<"$snapshot_json")" \
  --arg id "$(jq -r '.result.id' <<<"$included_status")" \
  --arg sha "$(jq -r '.result.content_sha256' <<<"$included_status")" \
  '{format_version:1,snapshot:{path:".harness/core-state/harness.db",file_sha256:$file_sha,logical_sha256:$logical_sha,schema_version:14},included_changesets:[{id:$id,path:".harness/changesets/included.changeset.jsonl",content_sha256:$sha}]}' \
  >"$state/.harness/core-state/manifest.json"

HARNESS_CLI="$cli" HARNESS_CORE_STATE_ROOT="$state" HARNESS_DB_PATH="$temp/materialized.db" \
  "$root/scripts/materialize-core-state.sh" >/dev/null
[[ $(sqlite3 "$temp/materialized.db" "SELECT count(*) FROM story WHERE id='CORE-BASE';") == 1 ]]
[[ $(sqlite3 "$temp/materialized.db" "SELECT count(*) FROM story WHERE id='CORE-LATER';") == 1 ]]
[[ $(sqlite3 "$temp/materialized.db" "SELECT count(*) FROM changeset_applied WHERE id='run_fixture_later';") == 1 ]]
[[ $(sqlite3 "$temp/materialized.db" "SELECT path FROM changeset_applied WHERE id='run_fixture_later';") == \
  '.harness/changesets/later.changeset.jsonl' ]]
! sqlite3 "$temp/materialized.db" .dump | grep -Fq "$state"

cp "$state/.harness/core-state/harness.db" "$temp/tampered.db"
printf x >>"$temp/tampered.db"
mv "$state/.harness/core-state/harness.db" "$temp/original.db"
cp "$temp/tampered.db" "$state/.harness/core-state/harness.db"
if HARNESS_CLI="$cli" HARNESS_CORE_STATE_ROOT="$state" HARNESS_DB_PATH="$temp/tampered-output.db" \
  "$root/scripts/materialize-core-state.sh" >"$temp/tampered.out" 2>&1; then
  echo "materializer unexpectedly accepted a tampered snapshot" >&2
  exit 1
fi
[[ ! -e "$temp/tampered-output.db" ]]
grep -Fq 'snapshot SHA-256 mismatch' "$temp/tampered.out"
mv "$temp/original.db" "$state/.harness/core-state/harness.db"

printf '{"op":"story.add","version":1,"id":"EXTRA","payload":{"title":"Changed","risk_lane":"normal"}}\n' \
  >>"$state/.harness/changesets/included.changeset.jsonl"
if HARNESS_CLI="$cli" HARNESS_CORE_STATE_ROOT="$state" HARNESS_DB_PATH="$temp/changed-output.db" \
  "$root/scripts/materialize-core-state.sh" >"$temp/changed.out" 2>&1; then
  echo "materializer unexpectedly accepted changed compacted JSONL" >&2
  exit 1
fi
[[ ! -e "$temp/changed-output.db" ]]
grep -Fq 'included changeset identity changed' "$temp/changed.out"

grep -Fq 'Get-FileHash' "$root/scripts/materialize-core-state.ps1"
grep -Fq 'source_logical_sha256' "$root/scripts/materialize-core-state.ps1"
grep -Fq 'compacted changeset id or bytes changed' "$root/scripts/materialize-core-state.ps1"
grep -Fq 'db changeset apply $relative' "$root/scripts/materialize-core-state.ps1"
grep -Fq 'Move-Item' "$root/scripts/materialize-core-state.ps1"

echo "verified snapshot materialization, later replay, tamper refusal, and PowerShell contract passed"

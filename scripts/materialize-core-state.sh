#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
state_root=${HARNESS_CORE_STATE_ROOT:-$root}
cli=${HARNESS_CLI:-$root/scripts/bin/harness-cli}
output=${HARNESS_DB_PATH:-$root/harness.db}
manifest=${HARNESS_CORE_MANIFEST:-$state_root/.harness/core-state/manifest.json}
changesets=${HARNESS_CHANGESET_DIR:-$state_root/.harness/changesets}

fail() {
  printf 'Core-state materialization failed: %s\n' "$*" >&2
  exit 1
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    fail "sha256sum or shasum is required"
  fi
}

[[ ! -e "$output" ]] || fail "output already exists: $output"
[[ -x "$cli" ]] || fail "Harness CLI is missing: $cli"
[[ -f "$manifest" ]] || fail "manifest is missing: $manifest"
command -v jq >/dev/null 2>&1 || fail "jq is required"

jq -e '
  .format_version == 1 and
  .snapshot.path == ".harness/core-state/harness.db" and
  (.snapshot.file_sha256 | test("^[0-9a-f]{64}$")) and
  (.snapshot.logical_sha256 | test("^[0-9a-f]{64}$")) and
  (.snapshot.schema_version | type == "number") and
  (.included_changesets | type == "array") and
  ([.included_changesets[].id] | length == (unique | length)) and
  ([.included_changesets[].path] | length == (unique | length)) and
  all(.included_changesets[];
    (.id | type == "string") and
    (.path | test("^\\.harness/changesets/[^/]+\\.changeset\\.jsonl$")) and
    (.content_sha256 | test("^[0-9a-f]{64}$")))
' "$manifest" >/dev/null || fail "manifest structure is invalid"

snapshot="$state_root/$(jq -r '.snapshot.path' "$manifest")"
[[ -f "$snapshot" ]] || fail "snapshot is missing: $snapshot"
expected_file_sha=$(jq -r '.snapshot.file_sha256' "$manifest")
actual_file_sha=$(sha256_file "$snapshot")
[[ "$actual_file_sha" == "$expected_file_sha" ]] ||
  fail "snapshot SHA-256 mismatch: expected $expected_file_sha, found $actual_file_sha"

output_parent=$(dirname "$output")
mkdir -p "$output_parent"
temp=$(mktemp -d "$output_parent/.harness-materialize.XXXXXX")
trap 'rm -rf "$temp"' EXIT
candidate="$temp/harness.db"
probe="$temp/probe.db"
cp "$snapshot" "$candidate"
chmod u+w "$candidate"

probe_json=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$candidate" \
  "$cli" db snapshot --output "$probe" --json) || fail "snapshot integrity check failed"
actual_logical_sha=$(jq -r '.result.source_logical_sha256' <<<"$probe_json")
expected_logical_sha=$(jq -r '.snapshot.logical_sha256' "$manifest")
[[ "$actual_logical_sha" == "$expected_logical_sha" ]] ||
  fail "snapshot logical SHA-256 mismatch: expected $expected_logical_sha, found $actual_logical_sha"
rm -f "$probe"

while IFS=$'\t' read -r included_id included_path included_sha; do
  [[ -n "$included_id" ]] || continue
  included_file="$state_root/$included_path"
  [[ -f "$included_file" ]] || fail "included changeset is missing: $included_path"
  status=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$candidate" \
    "$cli" db changeset status "$included_file" --json) ||
    fail "included changeset identity changed: $included_path"
  actual_id=$(jq -r '.result.id' <<<"$status")
  actual_sha=$(jq -r '.result.content_sha256' <<<"$status")
  [[ "$actual_id" == "$included_id" && "$actual_sha" == "$included_sha" ]] ||
    fail "included changeset identity changed: $included_path"
done < <(jq -r '.included_changesets[] | [.id,.path,.content_sha256] | @tsv' "$manifest")

if [[ -d "$changesets" ]]; then
  while IFS= read -r changeset; do
    relative=${changeset#"$state_root/"}
    status=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$candidate" \
      "$cli" db changeset status "$changeset" --json) || fail "invalid changeset: $relative"
    id=$(jq -r '.result.id' <<<"$status")
    sha=$(jq -r '.result.content_sha256' <<<"$status")
    included=$(jq -r --arg id "$id" --arg path "$relative" --arg sha "$sha" '
      [.included_changesets[] | select(.id == $id)] as $matches |
      if ($matches | length) == 0 then "no"
      elif ($matches | length) == 1 and $matches[0].path == $path and $matches[0].content_sha256 == $sha then "yes"
      else "conflict"
      end
    ' "$manifest")
    case "$included" in
      yes) ;;
      no)
        (
          cd "$state_root"
          HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$candidate" \
            "$cli" db changeset apply "$relative" --json >/dev/null
        ) || fail "changeset replay failed: $relative"
        ;;
      *) fail "compacted changeset id or bytes changed: $relative" ;;
    esac
  done < <(find "$changesets" -maxdepth 1 -type f -name '*.changeset.jsonl' -print | LC_ALL=C sort)
fi

contract=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$candidate" "$cli" query contract --json)
[[ $(jq -r '.result.database_state' <<<"$contract") == current ]] ||
  fail "materialized database is not at the current schema"
expected_schema=$(jq -r '.snapshot.schema_version' "$manifest")
[[ $(jq -r '.result.database_schema_version' <<<"$contract") == "$expected_schema" ]] ||
  fail "materialized schema differs from the manifest"

HARNESS_CLI="$cli" HARNESS_SOURCE_DB="$candidate" \
  "$root/scripts/verify-core-state-ownership.sh" >/dev/null ||
  fail "materialized database violates core ownership"

mv "$candidate" "$output"
trap - EXIT
rm -rf "$temp"
printf 'Core state materialized: database=%s snapshot_sha256=%s\n' "$output" "$actual_file_sha"

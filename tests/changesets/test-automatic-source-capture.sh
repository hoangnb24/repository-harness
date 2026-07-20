#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
if [[ -z ${HARNESS_CLI:-} ]]; then
  cargo build --quiet --manifest-path "$root/Cargo.toml" -p harness-cli --locked
fi
cli=${HARNESS_CLI:-$root/target/debug/harness-cli}
[[ -x "$cli" ]] || {
  echo "automatic source capture test requires a built Harness CLI: $cli" >&2
  exit 1
}

temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT

prepare_schema() {
  local fixture=$1
  mkdir -p "$fixture/scripts/schema"
  cp "$root"/scripts/schema/*.sql "$fixture/scripts/schema/"
}

run_in() {
  local fixture=$1
  shift
  HARNESS_REPO_ROOT="$fixture" "$cli" "$@"
}

source_fixture="$temp/source"
prepare_schema "$source_fixture"
mkdir -p "$source_fixture/crates/harness-cli"
printf '[workspace]\n' >"$source_fixture/Cargo.toml"
printf '[package]\nname = "harness-cli"\nversion = "0.0.0"\n' \
  >"$source_fixture/crates/harness-cli/Cargo.toml"

run_in "$source_fixture" init >/dev/null
run_in "$source_fixture" intake --type harness_improvement \
  --summary "source auto capture" --lane normal >/dev/null

mapfile -t source_changesets < <(
  find "$source_fixture/.harness/changesets" -maxdepth 1 -type f \
    -name 'run_auto_*.changeset.jsonl' -print
)
[[ ${#source_changesets[@]} -eq 1 ]]
jq -s -e '
  map(.op) == ["changeset.header", "intake.add"] and
  .[0].run_id == (input_filename | split("/") | last |
    sub("\\.changeset\\.jsonl$"; ""))
' "${source_changesets[0]}" >/dev/null

isolated_db="$source_fixture/isolated.db"
HARNESS_REPO_ROOT="$source_fixture" HARNESS_DB_PATH="$isolated_db" \
  "$cli" init >/dev/null
HARNESS_REPO_ROOT="$source_fixture" HARNESS_DB_PATH="$isolated_db" \
  "$cli" intake --type harness_improvement --summary "isolated write" \
  --lane normal >/dev/null
[[ $(find "$source_fixture/.harness/changesets" -maxdepth 1 -type f | wc -l) -eq 1 ]]

consumer_fixture="$temp/consumer"
prepare_schema "$consumer_fixture"
run_in "$consumer_fixture" init >/dev/null
run_in "$consumer_fixture" intake --type harness_improvement \
  --summary "consumer local write" --lane normal >/dev/null
[[ ! -e "$consumer_fixture/.harness/changesets" ]]

echo "automatic source capture and consumer isolation passed"

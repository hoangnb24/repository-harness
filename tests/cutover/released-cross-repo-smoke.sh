#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: released-cross-repo-smoke.sh \
  --symphony-archive PATH --symphony-sha256 SHA256 \
  --harness-cli PATH --harness-cli-sha256 SHA256 --harness-label LABEL \
  [--template-root PATH] [--keep-fixture PATH]

Runs exclusively in newly-created fixture directories. It does not modify either
source checkout, publish anything, or contact a remote.
EOF
  exit 2
}

symphony_archive= symphony_sha= harness_cli= harness_sha= harness_label=
template_root= keep_fixture=
while [[ $# -gt 0 ]]; do
  case "$1" in
    --symphony-archive) symphony_archive=${2:?}; shift 2 ;;
    --symphony-sha256) symphony_sha=${2:?}; shift 2 ;;
    --harness-cli) harness_cli=${2:?}; shift 2 ;;
    --harness-cli-sha256) harness_sha=${2:?}; shift 2 ;;
    --harness-label) harness_label=${2:?}; shift 2 ;;
    --template-root) template_root=${2:?}; shift 2 ;;
    --keep-fixture) keep_fixture=${2:?}; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$symphony_archive" && -n "$symphony_sha" && -n "$harness_cli" && -n "$harness_sha" && -n "$harness_label" ]] || usage

root=$(cd "$(dirname "$0")/../.." && pwd)
[[ -n "$template_root" ]] || template_root=$root
symphony_archive=$(cd "$(dirname "$symphony_archive")" && pwd)/$(basename "$symphony_archive")
harness_cli=$(cd "$(dirname "$harness_cli")" && pwd)/$(basename "$harness_cli")
template_root=$(cd "$template_root" && pwd)

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}
[[ "$(sha256 "$symphony_archive")" == "$symphony_sha" ]] || { echo "Symphony archive checksum mismatch" >&2; exit 1; }
[[ "$(sha256 "$harness_cli")" == "$harness_sha" ]] || { echo "Harness CLI checksum mismatch" >&2; exit 1; }

work=$(mktemp -d "${TMPDIR:-/tmp}/e11-released-smoke.XXXXXX")
web_pid=
cleanup() {
  local status=$?
  [[ -z "$web_pid" ]] || kill "$web_pid" 2>/dev/null || true
  if [[ -n "$keep_fixture" ]]; then
    mkdir -p "$(dirname "$keep_fixture")"
    mv "$work" "$keep_fixture"
    echo "Preserved fixture evidence: $keep_fixture"
  else
    rm -rf "$work"
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

bundle=$work/symphony
mkdir -p "$bundle"
tar -xzf "$symphony_archive" -C "$bundle"
binary=$(find "$bundle" -type f \( -name harness-symphony -o -name harness-symphony.exe \) -print -quit)
[[ -n "$binary" && -x "$binary" ]] || { echo "released Symphony binary not found" >&2; exit 1; }

symphony_contract=$($binary version --json)
actual_harness_version=${harness_label#harness-cli-v}
actual_harness_version=${actual_harness_version%-candidate}
jq -e --arg harness_version "$actual_harness_version" '
  .harness_protocol_version == 1 and
  (.symphony_version | test("^[0-9]+\\.[0-9]+\\.[0-9]+$")) and
  (.supported_harness_cli_versions | index($harness_version) != null)
' <<<"$symphony_contract" >/dev/null

make_fixture() {
  local fixture=$1 story=$2 cli_name=harness-cli
  [[ "$(basename "$harness_cli")" == *.exe ]] && cli_name=harness-cli.exe
  mkdir -p "$fixture/scripts/bin" "$fixture/scripts/schema" "$fixture/.harness"
  cp "$template_root/AGENTS.md" "$fixture/AGENTS.md"
  cp "$template_root/.gitignore" "$fixture/.gitignore"
  cp -R "$template_root/scripts/schema/." "$fixture/scripts/schema/"
  cp "$harness_cli" "$fixture/scripts/bin/$cli_name"
  chmod +x "$fixture/scripts/bin/$cli_name"
  local cli="scripts/bin/$cli_name"
  local absolute_cli="$fixture/scripts/bin/$cli_name"
  cat >"$fixture/.harness/symphony.yml" <<EOF
version: 1
repo:
  root: "."
  harness_db: "harness.db"
  harness_cli: "$cli"
agent:
  adapter: "custom"
  command: ["bash", ".harness/fixture-agent.sh", "$story", "$absolute_cli"]
pull_request:
  create: "disabled"
changeset:
  directory: ".harness/changesets"
EOF
  cp "$root/tests/cutover/support/released-fixture-agent.sh" "$fixture/.harness/fixture-agent.sh"
  chmod +x "$fixture/.harness/fixture-agent.sh"
  (
    cd "$fixture"
    "$cli" init >/dev/null
    "$cli" story add --id "$story" --title "Released cross-repository fixture" --lane normal --verify true >/dev/null
    cat >>.gitignore <<'EOF'
/.symphony/
/harness.db
/harness.db-wal
/harness.db-shm
/.harness/runs/
EOF
    git init -q
    git config user.name "E11 released smoke"
    git config user.email "e11-smoke@example.invalid"
    git add .
    git add -f .harness/symphony.yml .harness/fixture-agent.sh
    git commit -q -m "test: bootstrap released-artifact fixture"
  )
}

assert_contract() {
  local fixture=$1
  local cli=$fixture/scripts/bin/harness-cli
  [[ -x "$cli" ]] || cli=$fixture/scripts/bin/harness-cli.exe
  local actual_version=${harness_label#harness-cli-v} contract
  contract=$(cd "$fixture" && "$cli" query contract --json)
  jq -e --arg version "$actual_version" '
    .protocol_version == 1 and .operation == "query.contract" and
    .result.cli_version == $version and .result.protocol_version == 1 and
    .result.schema_minimum == 1 and .result.schema_maximum == 13 and
    .result.database_schema_version == 13 and .result.database_state == "current" and
    (["stories.read.v1","stories.write.v1","work-graph.read.v1","story-dependencies.read-write.v1","story-hierarchy.read-write.v1","changesets.apply.v1","changesets.status-sha.v1","isolated-db.v1","isolated-db-snapshot.v1","semantic-operation-log.v1"] - .result.capabilities | length == 0)
  ' <<<"$contract" >/dev/null
  printf '%s\n' "$contract"
}

prepare_fixture=$work/prepare-fixture
run_fixture=$work/run-fixture
make_fixture "$prepare_fixture" US-RELEASE-PREPARE
make_fixture "$run_fixture" US-RELEASE-RUN
prepare_contract=$(assert_contract "$prepare_fixture")
run_contract=$(assert_contract "$run_fixture")
[[ "$(jq -S '{protocol_version,operation,result}' <<<"$prepare_contract")" == \
   "$(jq -S '{protocol_version,operation,result}' <<<"$run_contract")" ]]

third=$work/operator
mkdir "$third"
git -C "$third" init -q
(cd "$third" && "$binary" --repo-root "$prepare_fixture" doctor)
(cd "$third" && "$binary" --repo-root "$prepare_fixture" work list) | rg -q 'US-RELEASE-PREPARE'
(cd "$third" && "$binary" --repo-root "$prepare_fixture" run US-RELEASE-PREPARE --prepare-only)
[[ -n "$(find "$prepare_fixture/.symphony/worktrees" -mindepth 1 -maxdepth 1 -type d -print -quit)" ]]

(cd "$third" && "$binary" --repo-root "$run_fixture" doctor)
(cd "$third" && "$binary" --repo-root "$run_fixture" work list) | rg -q 'US-RELEASE-RUN'
run_output=$(cd "$third" && "$binary" --repo-root "$run_fixture" run US-RELEASE-RUN)
run_id=$(sed -n 's/^Run \([^ ]*\) completed.*/\1/p' <<<"$run_output" | tail -1)
[[ -n "$run_id" ]] || run_id=$(find "$run_fixture/.symphony/worktrees" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | head -1)
[[ -n "$run_id" ]]

worktree="$run_fixture/.symphony/worktrees/$run_id"
changeset="$worktree/.harness/changesets/$run_id.changeset.jsonl"
jq -s -e --arg run "$run_id" --arg story US-RELEASE-RUN '
  length == 4 and
  .[0].op == "changeset.header" and .[0].version == 1 and
  .[0].run_id == $run and .[0].base_schema_version == 13 and
  .[1].op == "story.update" and .[1].id == $story and .[1].payload.status == "in_progress" and
  .[2].op == "story.verify" and .[2].id == $story and .[2].payload.result == "pass" and
  .[3].op == "story.complete" and .[3].id == $story and .[3].payload.result == "pass"
' "$changeset" >/dev/null
git -C "$worktree" add ".harness/changesets/$run_id.changeset.jsonl"
git -C "$worktree" commit -q -m "test: review $run_id semantic changeset"
branch=$(git -C "$worktree" branch --show-current)
git -C "$run_fixture" merge -q --no-ff "$branch" -m "test: merge reviewed $run_id"

cli=$run_fixture/scripts/bin/harness-cli
[[ -x "$cli" ]] || cli=$run_fixture/scripts/bin/harness-cli.exe
snapshot_before=$work/before.db
snapshot_after=$work/after.db
before=$(cd "$run_fixture" && "$cli" db snapshot --output "$snapshot_before" --json | jq -r '.result.source_logical_sha256')
first=$(cd "$third" && "$binary" --repo-root "$run_fixture" sync)
rg -q "$run_id applied \(3 operation\(s\)\)" <<<"$first"
after=$(cd "$run_fixture" && "$cli" db snapshot --output "$snapshot_after" --json | jq -r '.result.source_logical_sha256')
[[ "$before" != "$after" ]]
second=$(cd "$third" && "$binary" --repo-root "$run_fixture" sync)
rg -q "$run_id applied \(0 operation\(s\)\)" <<<"$second"
after_noop=$(cd "$run_fixture" && "$cli" db snapshot --output "$work/after-noop.db" --json | jq -r '.result.source_logical_sha256')
[[ "$after" == "$after_noop" ]]

web_log=$work/web.log
(cd "$third" && "$binary" --repo-root "$run_fixture" web --host 127.0.0.1 --port 0) >"$web_log" 2>&1 &
web_pid=$!
base=
for _ in {1..300}; do
  base=$(sed -n 's/.*\(http:\/\/127\.0\.0\.1:[0-9][0-9]*\).*/\1/p' "$web_log" | tail -1)
  [[ -n "$base" ]] && break
  kill -0 "$web_pid" 2>/dev/null || { cat "$web_log" >&2; exit 1; }
  sleep 0.1
done
[[ -n "$base" ]]
curl -fsS "$base/health" | jq -e '.ok == true' >/dev/null
curl -fsS "$base/api/board" | jq -e '.items | type == "array"' >/dev/null
index=$(curl -fsS "$base/")
rg -q '<div id="root"></div>' <<<"$index"
assets=$(sed -n "s#.*\(/assets/[^\"' ]*\).*#\1#p" <<<"$index" | LC_ALL=C sort -u)
[[ -n "$assets" ]]
while IFS= read -r asset; do [[ -n "$asset" ]] && curl -fsS "$base$asset" >/dev/null; done <<<"$assets"
kill "$web_pid" 2>/dev/null || true
wait "$web_pid" 2>/dev/null || true
web_pid=

jq -n \
  --arg harness_label "$harness_label" --arg harness_sha256 "$harness_sha" \
  --arg symphony_sha256 "$symphony_sha" --arg run_id "$run_id" \
  --arg logical_before "$before" --arg logical_after "$after" \
  --argjson harness_contract "$run_contract" --argjson symphony_contract "$symphony_contract" \
  '{result:"pass",harness:{label:$harness_label,sha256:$harness_sha256,contract:$harness_contract},symphony:{sha256:$symphony_sha256,contract:$symphony_contract},run_id:$run_id,logical_before:$logical_before,logical_after:$logical_after,prepare_only:true,doctor:true,work_list:true,web:true,sync_applied_operations:3,sync_noop_operations:0}' | tee "$work/result.json"

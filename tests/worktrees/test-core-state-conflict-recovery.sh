#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cli="$root/target/debug/harness-cli"
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
repo="$temp/repo"
mkdir -p "$repo/scripts/schema" "$repo/.harness/changesets"
cp "$root/scripts/schema/"*.sql "$repo/scripts/schema/"
printf 'harness.db\nharness.db-wal\nharness.db-shm\n' >"$repo/.gitignore"

cat >"$repo/.harness/changesets/000-seed.changeset.jsonl" <<'JSONL'
{"op":"changeset.header","version":1,"run_id":"run_worktree_seed","base_schema_version":14}
{"op":"story.add","version":2,"id":"WT-A","payload":{"created_at":"2026-07-20 00:00:00","title":"Worktree A","risk_lane":"normal"}}
{"op":"story.add","version":2,"id":"WT-B","payload":{"created_at":"2026-07-20 00:00:00","title":"Worktree B","risk_lane":"normal"}}
JSONL

git -C "$repo" init -q -b main
git -C "$repo" config user.name 'Harness Fixture'
git -C "$repo" config user.email 'harness@example.invalid'
git -C "$repo" add .
git -C "$repo" commit -qm seed

base_db="$temp/base.db"
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$base_db" "$cli" init >/dev/null
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$base_db" \
  "$cli" db changeset apply "$repo/.harness/changesets/000-seed.changeset.jsonl" --json >/dev/null

independent_a="$temp/independent-a"
independent_b="$temp/independent-b"
git -C "$repo" worktree add -q -b independent-a "$independent_a"
git -C "$repo" worktree add -q -b independent-b "$independent_b"
cp "$base_db" "$independent_a/harness.db"
cp "$base_db" "$independent_b/harness.db"

HARNESS_REPO_ROOT="$independent_a" HARNESS_DB_PATH="$independent_a/harness.db" \
  HARNESS_RUN_ID=run_100_independent_a "$cli" story update --id WT-A --status in_progress >/dev/null
HARNESS_REPO_ROOT="$independent_b" HARNESS_DB_PATH="$independent_b/harness.db" \
  HARNESS_RUN_ID=run_110_independent_b "$cli" story update --id WT-B --status changed >/dev/null
git -C "$independent_a" add .harness/changesets/run_100_independent_a.changeset.jsonl
git -C "$independent_a" commit -qm 'independent A'
git -C "$independent_b" add .harness/changesets/run_110_independent_b.changeset.jsonl
git -C "$independent_b" commit -qm 'independent B'
git -C "$repo" merge -q --no-edit independent-a
git -C "$repo" merge -q --no-edit independent-b

independent_db="$temp/independent.db"
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$independent_db" \
  "$cli" db rebuild --from "$repo/.harness/changesets" >/dev/null
[[ $(sqlite3 "$independent_db" "SELECT status||':'||revision FROM story WHERE id='WT-A';") == in_progress:1 ]]
[[ $(sqlite3 "$independent_db" "SELECT status||':'||revision FROM story WHERE id='WT-B';") == changed:1 ]]

conflict_first="$temp/conflict-first"
conflict_second="$temp/conflict-second"
git -C "$repo" worktree add -q -b conflict-first "$conflict_first"
git -C "$repo" worktree add -q -b conflict-second "$conflict_second"
cp "$independent_db" "$conflict_first/harness.db"
cp "$independent_db" "$conflict_second/harness.db"

HARNESS_REPO_ROOT="$conflict_first" HARNESS_DB_PATH="$conflict_first/harness.db" \
  HARNESS_RUN_ID=run_200_conflict_first "$cli" story update --id WT-A --evidence 'first intent' >/dev/null
HARNESS_REPO_ROOT="$conflict_second" HARNESS_DB_PATH="$conflict_second/harness.db" \
  HARNESS_RUN_ID=run_210_conflict_second "$cli" story update --id WT-A --evidence 'second intent' >/dev/null
git -C "$conflict_first" add .harness/changesets/run_200_conflict_first.changeset.jsonl
git -C "$conflict_first" commit -qm 'first same-entity intent'
git -C "$conflict_second" add .harness/changesets/run_210_conflict_second.changeset.jsonl
git -C "$conflict_second" commit -qm 'second same-entity intent'
git -C "$repo" merge -q --no-edit conflict-first
git -C "$repo" merge -q --no-edit conflict-second

conflict_db="$temp/conflict.db"
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$conflict_db" "$cli" init >/dev/null
for file in 000-seed run_100_independent_a run_110_independent_b run_200_conflict_first; do
  HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$conflict_db" \
    "$cli" db changeset apply "$repo/.harness/changesets/$file.changeset.jsonl" --json >/dev/null
done
set +e
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$conflict_db" \
  "$cli" db changeset apply "$repo/.harness/changesets/run_210_conflict_second.changeset.jsonl" --json \
  >"$temp/conflict.json" 2>"$temp/conflict.stderr"
conflict_exit=$?
set -e
[[ $conflict_exit == 3 ]]
jq -e '
  .error.code == "CONFLICT" and
  .error.details.changeset_id == "run_210_conflict_second" and
  .error.details.entity_kind == "story" and
  .error.details.entity_id == "WT-A" and
  .error.details.expected_revision == 1 and
  .error.details.actual_revision == 2
' "$temp/conflict.json" >/dev/null
[[ $(sqlite3 "$conflict_db" "SELECT evidence||':'||revision FROM story WHERE id='WT-A';") == 'first intent:2' ]]
[[ $(sqlite3 "$conflict_db" "SELECT count(*) FROM changeset_applied WHERE id='run_210_conflict_second';") == 0 ]]

# The integration branch is still local. The second agent inspects both intents,
# drops only its stale generated file, rebuilds, and reruns the domain command.
git -C "$repo" rm -q .harness/changesets/run_210_conflict_second.changeset.jsonl
git -C "$repo" commit -qm 'drop stale unshared intent before rebase'
recovery_db="$temp/recovery.db"
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$recovery_db" \
  "$cli" db rebuild --from "$repo/.harness/changesets" >/dev/null
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$recovery_db" \
  HARNESS_RUN_ID=run_220_conflict_second_rebased "$cli" story update --id WT-A --evidence 'resolved second intent' >/dev/null
grep -Fq '"expected_revision":2' "$repo/.harness/changesets/run_220_conflict_second_rebased.changeset.jsonl"
git -C "$repo" add .harness/changesets/run_220_conflict_second_rebased.changeset.jsonl
git -C "$repo" commit -qm 'rebase second intent through domain command'

final_db="$temp/final.db"
HARNESS_REPO_ROOT="$repo" HARNESS_DB_PATH="$final_db" \
  "$cli" db rebuild --from "$repo/.harness/changesets" >/dev/null
[[ $(sqlite3 "$final_db" "SELECT evidence||':'||revision FROM story WHERE id='WT-A';") == 'resolved second intent:3' ]]
[[ $(sqlite3 "$final_db" "SELECT status||':'||revision FROM story WHERE id='WT-B';") == changed:1 ]]

echo "real worktrees converge independently, reject stale same-entity replay, and recover through a rebased domain command"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

HARNESS_CLI="${HARNESS_CLI:-$ROOT_DIR/scripts/bin/harness-cli}"
if [[ ! -x "$HARNESS_CLI" && -x "$ROOT_DIR/target/debug/harness-cli" ]]; then
  HARNESS_CLI="$ROOT_DIR/target/debug/harness-cli"
fi
if [[ ! -x "$HARNESS_CLI" ]]; then
  echo "Harness CLI not found; build it with: cargo build -p harness-cli" >&2
  exit 1
fi

HARNESS_DB_PATH="$TMP_DIR/harness.db" \
  "$HARNESS_CLI" db rebuild --from "$ROOT_DIR/.harness/changesets" >/dev/null

expected_ids=(
  US-028 US-029 US-030 US-031 US-032 US-033 US-034 US-035 US-036 US-037
  US-038 US-039 US-040 US-041 US-042 US-043 US-044 US-045 US-046 US-047
  US-048 US-049 US-050 US-051 US-052 US-053 US-054 US-055 US-056 US-057
  US-058 US-059 US-060 US-061 US-062 US-063 US-SYM-001
  US-064 US-065 US-066 US-067 US-068 US-069 US-070 US-071 US-072
  US-073 US-074 US-075 US-076 US-077 US-078 US-079 US-080
)

for id in "${expected_ids[@]}"; do
  count="$(sqlite3 "$TMP_DIR/harness.db" "SELECT COUNT(*) FROM story WHERE id='$id';")"
  if [[ "$count" != "1" ]]; then
    echo "missing rebuilt story row: $id" >&2
    exit 1
  fi
done

retired_count="$(
  sqlite3 "$TMP_DIR/harness.db" \
    "SELECT COUNT(*) FROM story WHERE id IN ('US-061', 'US-063') AND status='retired';"
)"
if [[ "$retired_count" != "2" ]]; then
  echo "expected US-061 and US-063 to rebuild as retired" >&2
  exit 1
fi

expected_e09_edges=(
  'US-073|US-074'
  'US-074|US-075'
  'US-074|US-076'
  'US-075|US-077'
  'US-076|US-077'
  'US-077|US-078'
  'US-078|US-079'
  'US-075|US-080'
  'US-078|US-080'
)

for edge in "${expected_e09_edges[@]}"; do
  blocker="${edge%%|*}"
  blocked="${edge##*|}"
  count="$(sqlite3 "$TMP_DIR/harness.db" "SELECT COUNT(*) FROM story_dependency WHERE story_id='$blocker' AND blocks_story_id='$blocked';")"
  if [[ "$count" != "1" ]]; then
    echo "missing rebuilt E09 dependency edge: $blocker -> $blocked" >&2
    exit 1
  fi
done

echo "changeset rebuild restored ${#expected_ids[@]} Symphony story rows"

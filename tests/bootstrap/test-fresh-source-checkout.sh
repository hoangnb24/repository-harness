#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
checkout="$temp/checkout"
mkdir -p "$checkout"

tar -C "$root" \
  --exclude=.git \
  --exclude=target \
  --exclude=./harness.db \
  --exclude=./harness.db-wal \
  --exclude=./harness.db-shm \
  --exclude=scripts/bin \
  -cf - . | tar -C "$checkout" -xf -
# The root writable DB and tracked baseline share a basename; BSD tar's exclude
# pattern removes both, so restore only the tracked input explicitly.
mkdir -p "$checkout/.harness/core-state"
cp "$root/.harness/core-state/harness.db" "$checkout/.harness/core-state/harness.db"

[[ ! -e "$checkout/harness.db" ]]
"$checkout/scripts/bootstrap-harness.sh" >/dev/null
[[ -f "$checkout/harness.db" ]]
HARNESS_CLI="$checkout/scripts/bin/harness-cli" \
  "$checkout/scripts/verify-core-snapshot.sh" >/dev/null
HARNESS_CLI="$checkout/scripts/bin/harness-cli" \
  "$checkout/scripts/verify-materialized-core-parity.sh" >/dev/null
[[ $(sqlite3 "$checkout/harness.db" "SELECT status FROM story WHERE id='US-119';") == implemented ]]

echo "fresh source checkout bootstraps solely from tracked snapshot and JSONL state"

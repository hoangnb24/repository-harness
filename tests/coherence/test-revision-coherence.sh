#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
verify="$root/scripts/verify-revision-coherence.sh"

HARNESS_COHERENCE_SKIP_RUNTIME=1 "$verify" >"$temp/pass.out"
grep -Fq 'revision metadata coherent' "$temp/pass.out"

cp "$root/Cargo.lock" "$temp/Cargo.lock"
perl -0pi -e 's/(name = "harness-cli"\nversion = ")[^"]+/$1.0.0.0/' "$temp/Cargo.lock"
if HARNESS_COHERENCE_SKIP_RUNTIME=1 HARNESS_COHERENCE_LOCKFILE="$temp/Cargo.lock" \
  "$verify" >"$temp/lock.out" 2>&1; then
  echo "coherence unexpectedly accepted a Cargo.lock version mismatch" >&2
  exit 1
fi
grep -Fq 'does not match crate version' "$temp/lock.out"

printf 'harness-cli-v9.9.9\n' >"$temp/release-tag"
if HARNESS_COHERENCE_SKIP_RUNTIME=1 HARNESS_COHERENCE_RELEASE_TAG_FILE="$temp/release-tag" \
  "$verify" >"$temp/tag.out" 2>&1; then
  echo "coherence unexpectedly accepted a pinned-release mismatch" >&2
  exit 1
fi
grep -Fq 'pinned release harness-cli-v9.9.9 does not match' "$temp/tag.out"

mkdir "$temp/schema"
cp "$root/scripts/schema/001-init.sql" "$temp/schema/001-init.sql"
cp "$root/scripts/schema/003-tool-registry.sql" "$temp/schema/003-tool-registry.sql"
if HARNESS_COHERENCE_SKIP_RUNTIME=1 HARNESS_COHERENCE_SCHEMA_DIR="$temp/schema" \
  "$verify" >"$temp/schema.out" 2>&1; then
  echo "coherence unexpectedly accepted a schema gap" >&2
  exit 1
fi
grep -Fq 'expected prefix 002-' "$temp/schema.out"

for generated_binary in \
  scripts/bin/harness-v0-migrate \
  scripts/bin/harness-v0-migrate.exe; do
  git -C "$root" check-ignore -q -- "$generated_binary" || {
    echo "generated bridge binary is not ignored: $generated_binary" >&2
    exit 1
  }
done

for visible_path in \
  crates/harness-v0-migrate/src/main.rs \
  scripts/bin/unrelated-file; do
  if git -C "$root" check-ignore -q -- "$visible_path"; then
    echo "generated bridge ignore is too broad: $visible_path" >&2
    exit 1
  fi
done

echo "revision coherence, drift fixtures, and exact generated bridge ignores passed"

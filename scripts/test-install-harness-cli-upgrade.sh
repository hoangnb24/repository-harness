#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

REF="harness-cli-v9.8.7"
SOURCE="$TMP/$REF"
ASSETS="$TMP/assets/$REF"
TARGET="$TMP/target"
PLATFORM="test-platform"
mkdir -p "$SOURCE/scripts/schema" "$SOURCE/docs" "$ASSETS" "$TARGET/scripts/bin"

printf '%s\n' '.gitignore' 'docs/HARNESS.md' > "$SOURCE/scripts/harness-install-files.txt"
printf '%s\n' '# fixture' > "$SOURCE/.gitignore"
printf '%s\n' 'tagged template' > "$SOURCE/docs/HARNESS.md"
printf '%s\n' 'SELECT 1;' > "$SOURCE/scripts/schema/001-fixture.sql"
cp "$ROOT/scripts/agent-harness-block.md" "$SOURCE/scripts/agent-harness-block.md"
printf '%s\n' 'old-cli' > "$TARGET/scripts/bin/harness-cli"
chmod 755 "$TARGET/scripts/bin/harness-cli"
printf '%s\n' 'new-cli' > "$ASSETS/harness-cli-$PLATFORM"
shasum -a 256 "$ASSETS/harness-cli-$PLATFORM" > "$ASSETS/harness-cli-$PLATFORM.sha256"

HARNESS_SOURCE_BASE_URL="file://$SOURCE" \
HARNESS_CLI_BASE_URL="file://$ASSETS" \
HARNESS_CLI_PLATFORM="$PLATFORM" \
  "$ROOT/scripts/install-harness.sh" --directory "$TARGET" --merge --yes >/dev/null
grep -Fxq 'old-cli' "$TARGET/scripts/bin/harness-cli"

HARNESS_SOURCE_BASE_URL="file://$SOURCE" \
HARNESS_CLI_BASE_URL="file://$ASSETS" \
HARNESS_CLI_PLATFORM="$PLATFORM" \
  "$ROOT/scripts/install-harness.sh" --directory "$TARGET" --merge \
    --upgrade-cli --ref "$REF" --yes >/dev/null
grep -Fxq 'new-cli' "$TARGET/scripts/bin/harness-cli"
test -f "$TARGET/docs/HARNESS.md"
test -f "$TARGET/scripts/schema/001-fixture.sql"

printf '%s\n' 'old-cli-again' > "$TARGET/scripts/bin/harness-cli"
printf '%s\n' '0  harness-cli-test-platform' > "$ASSETS/harness-cli-$PLATFORM.sha256"
if HARNESS_SOURCE_BASE_URL="file://$SOURCE" \
   HARNESS_CLI_BASE_URL="file://$ASSETS" \
   HARNESS_CLI_PLATFORM="$PLATFORM" \
     "$ROOT/scripts/install-harness.sh" --directory "$TARGET" --merge \
       --upgrade-cli --ref "$REF" --yes >/dev/null 2>&1; then
  printf 'expected checksum mismatch to fail\n' >&2
  exit 1
fi
grep -Fxq 'old-cli-again' "$TARGET/scripts/bin/harness-cli"

if "$ROOT/scripts/install-harness.sh" --directory "$TARGET" --merge \
     --upgrade-cli --ref main --yes >/dev/null 2>&1; then
  printf 'expected mutable ref to fail\n' >&2
  exit 1
fi

if "$ROOT/scripts/install-harness.sh" --directory "$TARGET" --merge \
     --ref "$REF" --yes >/dev/null 2>&1; then
  printf 'expected ref without explicit upgrade to fail\n' >&2
  exit 1
fi

grep -Fq '[switch]$UpgradeCli' "$ROOT/scripts/install-harness.ps1"
grep -Fq '[string]$Ref' "$ROOT/scripts/install-harness.ps1"
grep -Fq '[System.IO.File]::Replace' "$ROOT/scripts/install-harness.ps1"
grep -Fq 'releases/download/$Ref' "$ROOT/scripts/install-harness.ps1"
grep -Fq 'tests/protocol/smoke-native-artifact.sh' "$ROOT/.github/workflows/harness-cli-release.yml"
grep -Fq 'tests/protocol/smoke-native-artifact.ps1' "$ROOT/.github/workflows/harness-cli-release.yml"
grep -Fq 'query", "work-graph", "--json"' "$ROOT/tests/protocol/smoke-native-artifact.ps1"
grep -Fq 'db", "snapshot", "--output"' "$ROOT/tests/protocol/smoke-native-artifact.ps1"
grep -Fq 'ExpectedExit 3' "$ROOT/tests/protocol/smoke-native-artifact.ps1"

printf 'installer forced-upgrade contract passed\n'

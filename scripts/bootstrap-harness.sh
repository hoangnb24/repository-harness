#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
db=${HARNESS_DB_PATH:-$root/harness.db}
cli=${HARNESS_CLI:-$root/scripts/bin/harness-cli}
source_checkout=0
if [[ -f "$root/Cargo.toml" && -f "$root/crates/harness-cli/Cargo.toml" ]]; then
  source_checkout=1
fi

fail() {
  printf 'Harness bootstrap failed: %s\n' "$*" >&2
  exit 1
}

contract_state() {
  local contract
  contract=$(HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$db" "$cli" query contract --json)
  case "$contract" in
    *'"database_state":"missing"'*) printf 'missing\n' ;;
    *'"database_state":"current"'*) printf 'current\n' ;;
    *'"database_state":"needs_migration"'*) printf 'needs_migration\n' ;;
    *'"database_state":"unsupported"'*) printf 'unsupported\n' ;;
    *) fail "query contract returned an unknown database state" ;;
  esac
}

if [[ $source_checkout == 1 && "$db" == "$root/harness.db" && ! -e "$db" &&
      (! -f "$root/.harness/core-state/manifest.json" || ! -f "$root/.harness/core-state/harness.db") ]]; then
  fail "authoritative core state is unavailable; tracked verified core state is missing"
fi

if [[ $source_checkout == 1 ]]; then
  HARNESS_COHERENCE_SKIP_RUNTIME=1 "$root/scripts/verify-revision-coherence.sh" >/dev/null
  command -v cargo >/dev/null 2>&1 || fail "cargo is required in a Harness CLI source checkout"
  cargo build --quiet --manifest-path "$root/Cargo.toml" -p harness-cli --locked
  built_cli="$root/target/debug/harness-cli"
  if [[ ! -e "$cli" || ! "$built_cli" -ef "$cli" ]]; then
    mkdir -p "$(dirname "$cli")"
    install -m 755 "$built_cli" "$cli"
  fi
elif [[ ! -x "$cli" ]]; then
  fail "Harness CLI is missing; install Harness again from its pinned release"
fi

release_tag_file="$root/scripts/harness-cli-release-tag"
[[ -f "$release_tag_file" ]] || fail "pinned release file is missing: $release_tag_file"
release_tag=$(awk 'NF && $1 !~ /^#/ { print $1; exit }' "$release_tag_file")
expected_version=${release_tag#harness-cli-v}
actual_version=$("$cli" --version | awk '{ print $NF }')
[[ "$release_tag" == harness-cli-v* && "$actual_version" == "$expected_version" ]] ||
  fail "CLI version $actual_version does not match pinned release $release_tag"

if [[ $source_checkout == 1 && "$db" == "$root/harness.db" && ! -e "$db" ]]; then
  HARNESS_CLI="$cli" HARNESS_DB_PATH="$db" "$root/scripts/materialize-core-state.sh" >/dev/null ||
    fail "tracked core-state materialization failed"
fi

case "$(contract_state)" in
  missing)
    HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$db" "$cli" init >/dev/null
    ;;
  needs_migration)
    HARNESS_REPO_ROOT="$root" HARNESS_DB_PATH="$db" "$cli" migrate >/dev/null
    ;;
  current)
    ;;
  unsupported)
    fail "database schema is outside the CLI's supported range"
    ;;
esac

[[ "$(contract_state)" == current ]] || fail "database did not reach current schema"
if [[ $source_checkout == 1 && "$db" == "$root/harness.db" ]]; then
  HARNESS_CLI="$cli" HARNESS_SOURCE_DB="$db" "$root/scripts/verify-core-state-ownership.sh" >/dev/null
fi
printf 'Harness ready: cli=%s database=%s\n' "$cli" "$db"

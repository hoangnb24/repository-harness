#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
source_premerge="$root/scripts/validate-premerge.sh"
temporary=$(mktemp -d "${TMPDIR:-/tmp}/phase5-premerge-forwarding.XXXXXX")
trap 'rm -rf "$temporary"' EXIT

fail() {
  echo "Phase 5 premerge forwarding test: $*" >&2
  exit 1
}

while IFS= read -r variable; do
  unset "$variable"
done < <(compgen -A variable HARNESS_PHASE5_ || true)

mkdir -p "$temporary/scripts" "$temporary/tests" "$temporary/bin"
cp "$source_premerge" "$temporary/scripts/validate-premerge.sh"
chmod +x "$temporary/scripts/validate-premerge.sh"

make_success_stub() {
  local path="$temporary/$1"
  mkdir -p "$(dirname "$path")"
  printf '#!/usr/bin/env bash\nexit 0\n' >"$path"
  chmod +x "$path"
}

for path in \
  scripts/verify-v1-phase1-contracts.sh \
  scripts/verify-v1-phase2-core.sh \
  scripts/verify-v1-phase3-recovery.sh \
  scripts/verify-v1-phase4-bridge.sh \
  scripts/verify-revision-coherence.sh \
  tests/evals/test-phase5-premerge-trust-forwarding.sh \
  tests/coherence/test-revision-coherence.sh \
  tests/coherence/test-core-state-ownership.sh \
  tests/core/test-schema-replay-command-contract.sh \
  tests/bootstrap/test-bootstrap-harness.sh \
  tests/protocol/smoke-native-artifact.sh \
  tests/installer/test-install-harness-modes.sh \
  tests/installer/assert-consumer-changeset-trackable.sh \
  tests/maintenance/test-harness-cli-release-classification.sh \
  tests/maintenance/test-render-changelog-files.sh \
  tests/docs/test-doc-contracts.sh \
  tests/evals/test-task-authority.sh \
  tests/release/test-post-merge-release-recovery.sh; do
  make_success_stub "$path"
done

for command in cargo git jq rg sqlite3; do
  make_success_stub "bin/$command"
done

argv_log="$temporary/phase5-argv"
call_log="$temporary/phase5-called"
cat >"$temporary/scripts/verify-v1-phase5-evidence.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n ${HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY+x} || -n ${HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256+x} ]]; then
  echo 'reserved Phase 5 environment leaked to verifier' >&2
  exit 90
fi
printf 'called\n' >"$PHASE5_PREMERGE_CALL_LOG"
: >"$PHASE5_PREMERGE_ARGV_LOG"
if (( $# > 0 )); then
  printf '%s\n' "$@" >"$PHASE5_PREMERGE_ARGV_LOG"
fi
STUB
chmod +x "$temporary/scripts/verify-v1-phase5-evidence.sh"

test_path="$temporary/bin:$PATH"
run_premerge() {
  PATH="$test_path" \
    PHASE5_PREMERGE_CALL_LOG="$call_log" \
    PHASE5_PREMERGE_ARGV_LOG="$argv_log" \
    "$temporary/scripts/validate-premerge.sh" "$@"
}

assert_not_called() {
  [[ ! -e "$call_log" ]] || fail "Phase 5 verifier ran after rejected operator input"
}

rm -f "$call_log" "$argv_log"
run_premerge >/dev/null
[[ -e "$call_log" ]] || fail "no-input candidate path did not invoke Phase 5"
[[ ! -s "$argv_log" ]] || fail "no-input candidate path forwarded arguments"

registry="/external trust/owners.json"
registry_sha="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
expected="$temporary/expected-argv"
printf '%s\n' \
  --trusted-owner-registry "$registry" \
  --trusted-owner-registry-sha256 "$registry_sha" >"$expected"
rm -f "$call_log" "$argv_log"
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY="$registry" \
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256="$registry_sha" \
  run_premerge >/dev/null
[[ -e "$call_log" ]] || fail "paired trust input did not invoke Phase 5"
cmp -s "$expected" "$argv_log" || fail "paired trust input did not preserve exact argv boundaries"

rm -f "$call_log" "$argv_log"
if HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY="$registry" run_premerge >/dev/null 2>&1; then
  fail "registry-only input was accepted"
fi
assert_not_called

rm -f "$call_log" "$argv_log"
if HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256="$registry_sha" run_premerge >/dev/null 2>&1; then
  fail "SHA-only input was accepted"
fi
assert_not_called

rm -f "$call_log" "$argv_log"
if run_premerge --dogfood-only >/dev/null 2>&1; then
  fail "dogfood-only bypass argument was accepted"
fi
assert_not_called

rm -f "$call_log" "$argv_log"
if HARNESS_PHASE5_OPTIONS=--dogfood-only run_premerge >/dev/null 2>&1; then
  fail "unknown Phase 5 environment option was accepted"
fi
assert_not_called

printf 'Phase 5 premerge paired forwarding, partial, bypass, unknown-option, and no-input contracts passed\n'

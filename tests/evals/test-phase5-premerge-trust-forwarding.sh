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
ln -s /bin/bash "$temporary/bin/bash"

case_log="$temporary/cases-run"
cases_run=0
mark_case() {
  cases_run=$((cases_run + 1))
  printf '%s\n' "$1" >>"$case_log"
}

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
  tests/release/test-v1-build-receipts.sh \
  tests/release/test-v1-build-receipt-workflow.sh \
  tests/release/test-release-workflow-contract.sh \
  tests/release/test-post-merge-release-recovery.sh; do
  make_success_stub "$path"
done

for command in cargo git jq rg sqlite3; do
  make_success_stub "bin/$command"
done

argv_log="$temporary/phase5-argv"
call_log="$temporary/phase5-called"
phase7_call_log="$temporary/phase7-called"
cat >"$temporary/tests/release/test-v1-phase7-release-proof.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'called\n' >>"$PHASE7_PREMERGE_CALL_LOG"
STUB
chmod +x "$temporary/tests/release/test-v1-phase7-release-proof.sh"

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
    PHASE7_PREMERGE_CALL_LOG="$phase7_call_log" \
    /bin/bash "$temporary/scripts/validate-premerge.sh" "$@"
}

assert_not_called() {
  [[ ! -e "$call_log" ]] || fail "Phase 5 verifier ran after rejected operator input"
  [[ ! -e "$phase7_call_log" ]] || fail "Phase 7 test ran after rejected operator input"
}

rm -f "$call_log" "$argv_log" "$phase7_call_log"
run_premerge >/dev/null
[[ -e "$call_log" ]] || fail "no-input candidate path did not invoke Phase 5"
[[ -e "$phase7_call_log" ]] || fail "no-input candidate path did not invoke Phase 7"
[[ ! -s "$argv_log" ]] || fail "no-input candidate path forwarded arguments"
mark_case no-input-zero-argv

registry="/external trust/owners.json"
registry_sha="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
expected="$temporary/expected-argv"
printf '%s\n' \
  --trusted-owner-registry "$registry" \
  --trusted-owner-registry-sha256 "$registry_sha" >"$expected"
rm -f "$call_log" "$argv_log" "$phase7_call_log"
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY="$registry" \
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256="$registry_sha" \
  run_premerge >/dev/null
[[ -e "$call_log" ]] || fail "paired trust input did not invoke Phase 5"
[[ -e "$phase7_call_log" ]] || fail "paired trust input did not invoke Phase 7"
cmp -s "$expected" "$argv_log" || fail "paired trust input did not preserve exact argv boundaries"
mark_case paired-input-exact-argv

rm -f "$call_log" "$argv_log" "$phase7_call_log"
if HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY="$registry" run_premerge >/dev/null 2>&1; then
  fail "registry-only input was accepted"
fi
assert_not_called
mark_case registry-only-rejected

rm -f "$call_log" "$argv_log" "$phase7_call_log"
if HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256="$registry_sha" run_premerge >/dev/null 2>&1; then
  fail "SHA-only input was accepted"
fi
assert_not_called
mark_case sha-only-rejected

rm -f "$call_log" "$argv_log" "$phase7_call_log"
if run_premerge --dogfood-only >/dev/null 2>&1; then
  fail "dogfood-only bypass argument was accepted"
fi
assert_not_called
mark_case cli-bypass-rejected

rm -f "$call_log" "$argv_log" "$phase7_call_log"
if HARNESS_PHASE5_OPTIONS=--dogfood-only run_premerge >/dev/null 2>&1; then
  fail "unknown Phase 5 environment option was accepted"
fi
assert_not_called
mark_case unknown-environment-rejected

expected_cases="$temporary/expected-cases"
printf '%s\n' \
  no-input-zero-argv \
  paired-input-exact-argv \
  registry-only-rejected \
  sha-only-rejected \
  cli-bypass-rejected \
  unknown-environment-rejected >"$expected_cases"
[[ "$cases_run" -eq 6 ]] || fail "expected 6 completed cases, got $cases_run"
cmp -s "$expected_cases" "$case_log" || fail "case completion markers were missing or out of order"

printf 'Phase 5 premerge forwarding contracts passed (6/6 cases under /bin/bash)\n'

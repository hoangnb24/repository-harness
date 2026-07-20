#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
decision="$root/docs/decisions/0017-proportional-v1-release-gate.md"
plan="$root/docs/REFACTOR_PLAN.md"
workflow="$root/.github/workflows/harness-v1-release.yml"

fail() {
  echo "proportional V1 release gate contract failed: $*" >&2
  exit 1
}

for phrase in \
  'normal premerge validation' \
  'every platform claimed as supported' \
  'one repository dogfood comparison' \
  'independent reviewer' \
  'actual release' \
  'workflow generates and verifies provenance'; do
  grep -Fq "$phrase" "$decision" || fail "Decision 0017 omits: $phrase"
done

grep -Fq 'P0-P7 cards and detailed custody framework remain available for optional' "$plan" ||
  fail 'plan still treats P0-P7 as mandatory'
grep -Fq 'unproven platforms are explicitly' "$plan" ||
  fail 'plan does not narrow unsupported platform claims'
grep -Fq 'workflow_dispatch:' "$workflow" || fail 'diagnostic is not manually dispatched'
! grep -Fq '.github/harness-v1-diagnostic-request' "$workflow" ||
  fail 'sentinel still triggers diagnostics'
! grep -Fq 'push:' "$workflow" || fail 'push still triggers diagnostics'

echo 'proportional V1 release gate contract passed'

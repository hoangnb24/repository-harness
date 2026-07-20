#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
decision="$root/docs/decisions/0018-minimal-v1-release-gate.md"
plan="$root/docs/REFACTOR_PLAN.md"
workflow="$root/.github/workflows/harness-v1-release.yml"

fail() {
  echo "proportional V1 release gate contract failed: $*" >&2
  exit 1
}

for phrase in \
  'normal premerge validation' \
  'each platform claimed as supported' \
  'ordinary pull-request approval' \
  'downloadable binaries, SHA-256 checksums' \
  'manually' \
  'Windows x64 remains experimental and explicitly unsupported'; do
  grep -Fq "$phrase" "$decision" || fail "Decision 0018 omits: $phrase"
done

grep -Fq 'dogfood comparison is removed from the V1 release gate' "$decision" ||
  fail 'Decision 0018 does not remove mandatory dogfood'

grep -Fq '## Optional Dogfood Protocol' "$plan" ||
  fail 'plan still treats dogfood as mandatory'
grep -Fq 'P0-P7 cards, and the detailed custody framework remain' "$plan" ||
  fail 'plan still treats P0-P7 as mandatory'
grep -Fq 'unproven platforms are explicitly' "$plan" ||
  fail 'plan does not narrow unsupported platform claims'
grep -Fq 'workflow_dispatch:' "$workflow" || fail 'diagnostic is not manually dispatched'
! grep -Fq '.github/harness-v1-diagnostic-request' "$workflow" ||
  fail 'sentinel still triggers diagnostics'
! grep -Fq 'push:' "$workflow" || fail 'push still triggers diagnostics'

echo 'proportional V1 release gate contract passed'

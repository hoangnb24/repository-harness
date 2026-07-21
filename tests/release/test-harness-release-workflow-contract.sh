#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
release="$root/.github/workflows/harness-release.yml"
post_merge="$root/.github/workflows/post-merge-maintenance.yml"

[[ "$(grep -Ec '^          - platform: (macos-arm64|macos-x64|linux-x64|linux-arm64|windows-x64)$' "$release")" == 5 ]]
for platform in macos-arm64 macos-x64 linux-x64 linux-arm64 windows-x64; do
  grep -Fq -- "- platform: $platform" "$release"
done
grep -Fq 'run: scripts/validate-premerge.sh' "$release"
bootstrap_line=$(grep -n 'scripts/bootstrap-harness.sh' "$release" | head -n 1 | cut -d: -f1)
contract_line=$(grep -n 'run: scripts/validate-premerge.sh' "$release" | head -n 1 | cut -d: -f1)
[[ -n "$bootstrap_line" && "$bootstrap_line" -lt "$contract_line" ]]
grep -Fq 'scripts/verify-materialized-core-parity.sh' "$release"
grep -Fq 'scripts/build-harness-release.sh' "$release"
grep -Fq 'scripts/verify-harness-release-identity.sh' "$release"
grep -Fq 'scripts/promote-harness-release-tag.sh' "$release"
grep -Fq -- '--verify-tag' "$release"
grep -Fq 'pattern: harness-*' "$release"
grep -Fq 'test "$(gh release view "$RELEASE_TAG"' "$release"
! grep -Fq -- '--clobber' "$release"
! grep -Eq '^  push:' "$release"
! grep -Fq 'git tag ' "$release"

grep -Fq 'harness_changed: ${{ steps.maintenance.outputs.harness_changed }}' "$post_merge"
grep -Fq 'uses: ./.github/workflows/harness-release.yml' "$post_merge"
grep -Fq 'harness_release_tag="harness-v$new_harness_version"' "$post_merge"
grep -Fq 'checkout_ref: ${{ needs.prepare.outputs.maintenance_ref }}' "$post_merge"

echo "Harness core five-platform proof-before-promotion workflow contract passed"

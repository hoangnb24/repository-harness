#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
release="$root/.github/workflows/harness-cli-release.yml"
post_merge="$root/.github/workflows/post-merge-maintenance.yml"
premerge="$root/.github/workflows/premerge.yml"

[[ "$(grep -Ec '^          - platform: (macos-arm64|macos-x64|linux-x64|linux-arm64|windows-x64)$' "$release")" == 5 ]]
for platform in macos-arm64 macos-x64 linux-x64 linux-arm64 windows-x64; do
  grep -Fq -- "- platform: $platform" "$release"
done

grep -Fq 'run: scripts/validate-premerge.sh' "$release"
bootstrap_line=$(grep -n 'scripts/bootstrap-harness.sh' "$release" | head -n 1 | cut -d: -f1)
contract_line=$(grep -n 'run: scripts/validate-premerge.sh' "$release" | head -n 1 | cut -d: -f1)
[[ -n "$bootstrap_line" && "$bootstrap_line" -lt "$contract_line" ]]
grep -Fq 'scripts/verify-materialized-core-parity.sh' "$release"
grep -Fq 'source_sha: ${{ steps.source.outputs.sha }}' "$release"
grep -Fq 'ref: ${{ needs.verify.outputs.source_sha }}' "$release"
grep -Fq 'needs: [verify, build]' "$release"
grep -Fq 'scripts/verify-harness-cli-release-identity.sh' "$release"
grep -Fq 'pretag "$RELEASE_TAG" "$SOURCE_SHA" "$PROOF_RUN"' "$release"
grep -Fq 'scripts/promote-harness-cli-release-tag.sh' "$release"
grep -Fq -- '--verify-tag' "$release"
grep -Fq 'test "$(gh release view "$RELEASE_TAG"' "$release"
! grep -Fq -- '--clobber' "$release"
! grep -Eq '^  push:' "$release"
! grep -Fq 'git tag ' "$release"

grep -Fq 'tests/release/download-v0.1.14-artifact.sh' "$release"
grep -Fq 'tests/installer/test-cli-upgrade-candidate.sh' "$release"
grep -Fq 'tests/installer/test-install-harness-modes.ps1' "$release"
grep -Fq 'tests/protocol/smoke-native-artifact.sh' "$release"
grep -Fq 'tests/protocol/smoke-native-artifact.ps1' "$release"

! grep -Fq 'git tag ' "$post_merge"
! grep -Fq 'git push origin "$release_tag"' "$post_merge"
grep -Fq 'checkout_ref: ${{ needs.prepare.outputs.maintenance_ref }}' "$post_merge"
grep -Fq 'Harness CLI candidate:' "$post_merge"

[[ "$(grep -Fc 'fetch-depth: 0' "$premerge")" -eq 2 ]]
grep -Fq 'Prove Linux initial-to-candidate upgrade' "$premerge"
grep -Fq 'Download pinned Windows initial protocol artifact' "$premerge"
grep -Fq 'test-cli-upgrade-candidate.sh' "$premerge"
grep -Fq -- '-InitialArtifact dist/us092-harness-cli-windows-x64.exe' "$premerge"

echo "five-platform proof-before-promotion, immutable release, and pre-merge transition workflow contract passed"

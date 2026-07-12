#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
workflow="$root/.github/workflows/harness-cli-release.yml"

[[ "$(grep -Ec '^          - platform: (macos-arm64|macos-x64|linux-x64|linux-arm64|windows-x64)$' "$workflow")" == 5 ]]
for platform in macos-arm64 macos-x64 linux-x64 linux-arm64 windows-x64; do
  grep -Fq -- "- platform: $platform" "$workflow"
done
grep -Fq 'cargo test -p harness-cli --locked' "$workflow"
grep -Fq 'cargo clippy -p harness-cli --all-targets --locked -- -D warnings' "$workflow"
grep -Fq 'shasum -a 256 -c "${{ matrix.binary }}.sha256"' "$workflow"
grep -Fq 'sha256sum -c "${{ matrix.binary }}.sha256"' "$workflow"
grep -Fq 'tests/protocol/smoke-native-artifact.sh' "$workflow"
grep -Fq 'tests/protocol/smoke-native-artifact.ps1' "$workflow"
grep -Fq 'tests/installer/test-install-harness-modes.sh' "$workflow"
grep -Fq 'tests/installer/test-install-harness-modes.ps1' "$workflow"
grep -Fq 'tests/installer/test-cli-upgrade-candidate.sh' "$workflow"
grep -Fq 'scripts/verify-harness-cli-release-identity.sh "$RELEASE_TAG"' "$workflow"
grep -Fq 'tests/release/test-release-identity-guard.sh' "$workflow"
[[ "$(grep -Fc 'fetch-depth: 0' "$workflow")" -ge 2 ]]
grep -Fq 'releases/download/harness-cli-v0.1.14/${{ matrix.binary }}' "$workflow"
! grep -Fq 'cargo test --workspace' "$workflow"
! grep -Fq 'harness-symphony' "$workflow"

echo "five-platform release, checksum, installer, and initial-upgrade workflow contract passed"

#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
workflow="$root/.github/workflows/premerge.yml"

while IFS= read -r changeset; do
  [[ $(git -C "$root" check-attr eol -- "$changeset") == "$changeset: eol: lf" ]]
done < <(git -C "$root" ls-files '.harness/changesets/*.changeset.jsonl')

linux_absent=$(grep -n 'test ! -e harness.db' "$workflow" | head -n1 | cut -d: -f1)
linux_bootstrap=$(grep -n 'scripts/bootstrap-harness.sh' "$workflow" | head -n1 | cut -d: -f1)
linux_parity=$(grep -n 'scripts/verify-materialized-core-parity.sh' "$workflow" | head -n1 | cut -d: -f1)
linux_contract=$(grep -n 'run: scripts/validate-premerge.sh' "$workflow" | head -n1 | cut -d: -f1)
[[ $linux_absent -lt $linux_bootstrap && $linux_bootstrap -lt $linux_parity && $linux_parity -lt $linux_contract ]]

windows_absent=$(grep -n 'checkout unexpectedly contains harness.db' "$workflow" | head -n1 | cut -d: -f1)
windows_bootstrap=$(grep -n '\.\\scripts\\bootstrap-harness.ps1' "$workflow" | head -n1 | cut -d: -f1)
windows_installer=$(grep -n 'test-install-harness-modes.ps1' "$workflow" | head -n1 | cut -d: -f1)
[[ $windows_absent -lt $windows_bootstrap && $windows_bootstrap -lt $windows_installer ]]

grep -Fq 'scripts/verify-core-snapshot.sh' "$root/scripts/validate-premerge.sh"
grep -Fq 'scripts/verify-materialized-core-parity.sh' "$root/scripts/validate-premerge.sh"
grep -Fq 'tests/worktrees/test-core-state-conflict-recovery.sh' "$root/scripts/validate-premerge.sh"
grep -Fq 'tests/snapshot/test-core-snapshot-compaction.sh' "$root/scripts/validate-premerge.sh"

echo "canonical JSONL checkout bytes, fresh-checkout Linux and Windows bootstrap ordering, and reproducible-state CI gates passed"

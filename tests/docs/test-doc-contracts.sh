#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  printf 'documentation contract failed: %s\n' "$*" >&2
  exit 1
}

reject_exact() {
  local file=$1
  local stale=$2
  if rg -Fq -- "$stale" "$root/$file"; then
    fail "$file contains stale current-state claim: $stale"
  fi
}

# These are active descriptions of the current repository and installed
# template. Historical decisions, reviews, and completed story evidence are
# intentionally outside this check.
reject_exact README.md 'There is no application implementation'
reject_exact README.md 'No product contract is currently defined.'
reject_exact docs/ARCHITECTURE.md 'No application stack is selected yet.'
reject_exact docs/ARCHITECTURE.md 'No application code exists yet.'
reject_exact docs/HARNESS.md 'Test matrix placeholder.'
reject_exact docs/HARNESS.md '- CI workflows.'
reject_exact docs/README.md 'they do not imply that app code, tests, CI, or deployment automation exist'
reject_exact docs/TEST_MATRIX.md 'No product behavior has been defined or implemented yet.'
reject_exact docs/TEST_MATRIX.md '| TBD |'
reject_exact docs/product/README.md 'No repository-specific product contract is currently defined.'
reject_exact scripts/README.md '## Future Command Contract'
reject_exact scripts/README.md 'Push a tag matching `v*` or'

rg -Fq 'This repository implements the Harness v0 product' "$root/README.md" ||
  fail 'README does not identify the implemented upstream Harness product'
rg -Fq 'Installing Harness into another repository does not create or choose' "$root/README.md" ||
  fail 'README does not preserve the consumer application boundary'
rg -Fq 'The upstream Harness product is implemented as a Rust workspace' "$root/docs/ARCHITECTURE.md" ||
  fail 'architecture does not describe the implemented Harness core'
rg -Fq 'The reusable template does not select an application stack' "$root/docs/ARCHITECTURE.md" ||
  fail 'architecture does not preserve consumer stack neutrality'
rg -Fq 'scripts/bin/harness-cli query matrix --active --summary' "$root/docs/TEST_MATRIX.md" ||
  fail 'legacy matrix doc does not route readers to authoritative proof state'
rg -Fq 'Installed consumer projects keep their own stack-specific validation commands' "$root/scripts/README.md" ||
  fail 'validation docs impose the upstream Rust gate on consumers'

for executable in \
  scripts/validate-premerge.sh \
  scripts/verify-revision-coherence.sh \
  tests/evals/test-task-authority.sh; do
  [[ -x "$root/$executable" ]] || fail "documented gate is not executable: $executable"
done

for required_gate in \
  'cargo fmt --all -- --check' \
  'cargo test --workspace --locked' \
  'cargo clippy --workspace --all-targets --locked -- -D warnings' \
  'scripts/verify-revision-coherence.sh' \
  'tests/docs/test-doc-contracts.sh' \
  'tests/evals/test-task-authority.sh' \
  'tests/release/test-post-merge-release-recovery.sh'; do
  rg -Fq -- "$required_gate" "$root/scripts/validate-premerge.sh" ||
    fail "pre-merge wrapper omits required gate: $required_gate"
done

"$root/tests/installer/assert-agent-authority-contract.sh" >/dev/null
"$root/tests/installer/assert-install-manifest-links.sh" >/dev/null
"$root/tests/docs/test-proportional-v1-release-gate.sh" >/dev/null

grep -Fq 'run: scripts/validate-premerge.sh' "$root/.github/workflows/premerge.yml" ||
  fail 'pull-request workflow does not use the local validation contract'
grep -Fq 'tests/installer/test-install-harness-modes.ps1' "$root/.github/workflows/premerge.yml" &&
  grep -Fq -- '-InitialArtifact dist/us092-harness-cli-windows-x64.exe' \
    "$root/.github/workflows/premerge.yml" ||
  fail 'pull-request workflow does not exercise the PowerShell installer contract'
grep -Fq 'run: scripts/validate-premerge.sh' "$root/.github/workflows/harness-cli-release.yml" ||
  fail 'release workflow does not reuse the pre-merge validation contract'

echo "live documentation truth, links, authority, and validation references passed"

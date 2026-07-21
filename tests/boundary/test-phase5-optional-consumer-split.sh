#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
installed="$temp/core"

# A deliberately unusable CLI location proves core installation never tries to
# resolve an orchestration/compatibility artifact.
HARNESS_CLI_BASE_URL="file://$temp/no-cli" \
HARNESS_CLI_PLATFORM=phase5-fixture \
  "$root/scripts/install-harness.sh" --directory "$installed" --yes \
  >"$temp/install.out"

grep -Fq 'Harness profile: core' "$temp/install.out"
! grep -Fq 'download harness-cli-' "$temp/install.out"

# Inspect the installed result, not only its manifest. No optional consumer or
# legacy evaluation surface may appear in an ordinary repository.
for path in \
  docs/contracts \
  scripts/bin \
  scripts/schema \
  scripts/bootstrap-harness.sh \
  docs/TRACE_SPEC.md \
  docs/HARNESS_AUDIT.md \
  docs/HARNESS_MATURITY.md \
  docs/IMPROVEMENT_PROTOCOL.md \
  .harness \
  harness.db; do
  [[ ! -e "$installed/$path" ]] || {
    echo "Phase 5 core unexpectedly installed optional surface: $path" >&2
    exit 1
  }
done

if find "$installed" -type f -print | \
  rg -i '/[^/]*(symphony|orchestrat|evaluation|benchmark|trace-score)[^/]*$' \
  >"$temp/forbidden-installed-paths"; then
  echo 'Phase 5 core contains an optional-consumer path:' >&2
  cat "$temp/forbidden-installed-paths" >&2
  exit 1
fi

# The source repository keeps protocol primitives only in the explicitly
# selected compatibility profile. Symphony product/policy paths remain absent.
grep -Fxq 'docs/contracts/harness-orchestration-v1.md' \
  "$root/scripts/harness-cli-install-files.txt"
grep -Fxq 'docs/TRACE_SPEC.md' "$root/scripts/harness-cli-install-files.txt"
! grep -Eiq 'symphony|evaluation' "$root/scripts/harness-install-files.txt"

if [[ -d "$root/tests/evals" ]] && \
  find "$root/tests/evals" -type f -print -quit | grep -q .; then
  echo 'core workflow regressions remain mislabeled as evaluations' >&2
  exit 1
fi
for workflow_test in \
  tests/workflow/test-repository-workflow.sh \
  tests/workflow/test-task-authority.sh; do
  [[ -f "$root/$workflow_test" ]] || {
      echo "missing workflow regression: $workflow_test" >&2
      exit 1
    }
done

for symphony_path in \
  crates/harness-symphony \
  docs/SYMPHONY_SCOPE.md \
  docs/SYMPHONY_QUICKSTART.md \
  docs/product/symphony-web-ui-controller.md; do
  [[ ! -e "$root/$symphony_path" ]] || {
    echo "Symphony-owned product path remains in Harness: $symphony_path" >&2
    exit 1
  }
done

echo 'Phase 5 core excludes orchestration and evaluation consumers; compatibility primitives remain explicit'

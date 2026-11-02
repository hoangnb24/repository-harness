#!/usr/bin/env bash
# Prove the context budget in both directions without touching tracked files.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
check="$root/scripts/check-context-budget.sh"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

# Positive: the current repository fits its declared budget.
"$check" >/dev/null

# Negative: shrinking each limit below the measured size must fail with
# ERROR/WHY/FIX naming the offender.
expect_failure() {
  local name=$1 pattern=$2 replacement=$3 expected=$4
  sed -E "s#$pattern#$replacement#" "$root/scripts/context-budget.tsv" >"$scratch/$name.tsv"
  if "$check" "$scratch/$name.tsv" 2>"$scratch/$name.err" >/dev/null; then
    echo "context budget test failed: $name violation was accepted" >&2
    exit 1
  fi
  for label in 'ERROR: ' 'WHY: ' 'FIX: ' "$expected"; do
    grep -Fq -- "$label" "$scratch/$name.err" || {
      echo "context budget test failed: $name output omits '$label'" >&2
      cat "$scratch/$name.err" >&2
      exit 1
    }
  done
}

expect_failure entry '^(bytes	scripts/agent-harness-block.md	)[0-9]+' '\110' 'scripts/agent-harness-block.md is'
expect_failure skill '^(bytes	\.agents/skills/\*/SKILL.md	)[0-9]+' '\110' '.agents/skills/encode-invariant/SKILL.md is'
expect_failure description '^(chars	skill-description	)[0-9]+' '\110' 'description is'
expect_failure words '^(words	[^	]+	)[0-9]+' '\110' 'words; limit is 10'

# Usage error: a missing budget file is distinct from a violation.
set +e
"$check" "$scratch/missing.tsv" 2>/dev/null
code=$?
set -e
[[ $code -eq 2 ]] || { echo "context budget test failed: missing budget exit $code" >&2; exit 1; }

git -C "$root" diff --quiet -- scripts/context-budget.tsv
echo "context budget contract passed"

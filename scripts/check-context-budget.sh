#!/usr/bin/env bash
# Check always-loaded context against scripts/context-budget.tsv.
# Usage: scripts/check-context-budget.sh [budget-file]
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
budget=${1:-$root/scripts/context-budget.tsv}
[[ -f "$budget" ]] || { echo "ERROR: budget file not found: $budget" >&2; exit 2; }

failures=0
fail() {
  printf 'ERROR: %s\nWHY: %s\nFIX: %s\n' "$1" "$2" "$3" >&2
  failures=$((failures + 1))
}

limit_for() { # kind target -> max, or empty
  awk -F '\t' -v kind="$1" -v target="$2" \
    '$1 == kind && $2 == target { print $3; exit }' "$budget"
}

why='This text is loaded into agent context repeatedly; growth costs tokens on every turn.'
fix_raise='Shorten it (move detail to references/ opened at a named step), or raise the limit in scripts/context-budget.tsv with a reason in the same change.'

while IFS=$'\t' read -r kind target max _reason; do
  [[ -z "$kind" || "$kind" == \#* ]] && continue
  case "$kind" in
    bytes)
      [[ "$target" == *'*'* ]] && continue
      size=$(wc -c <"$root/$target" | tr -d ' ')
      (( size <= max )) || fail "$target is $size bytes; limit is $max" "$why" "$fix_raise"
      ;;
    words)
      IFS='+' read -r -a files <<<"$target"
      words=0
      for file in "${files[@]}"; do
        words=$((words + $(wc -w <"$root/$file" | tr -d ' ')))
      done
      (( words <= max )) || fail "$target has $words words; limit is $max" "$why" "$fix_raise"
      ;;
  esac
done <"$budget"

default_skill=$(limit_for bytes '.agents/skills/*/SKILL.md')
description_max=$(limit_for chars skill-description)
[[ -n "$default_skill" && -n "$description_max" ]] || {
  echo "ERROR: $budget must define the skill default and skill-description limits" >&2
  exit 2
}

skills=$(cat "$root/scripts/harness-install-files.txt" \
  "$root/scripts/engineering-wisdom-install-files.txt" |
  grep -E '^\.agents/skills/[^/]+/SKILL\.md$' | LC_ALL=C sort -u)
for skill in $skills; do
  max=$(limit_for bytes "$skill")
  max=${max:-$default_skill}
  size=$(wc -c <"$root/$skill" | tr -d ' ')
  (( size <= max )) || fail "$skill is $size bytes; limit is $max" "$why" "$fix_raise"

  description=$(awk '/^---$/ { n++; next } n == 1 && /^description:/ { sub(/^description:[ ]*/, ""); print; exit }' "$root/$skill")
  length=$(printf '%s' "$description" | wc -m | tr -d ' ')
  (( length <= description_max )) || fail \
    "$skill description is $length characters; limit is $description_max" \
    'Descriptions load every session; they should say only when to use the skill.' \
    'Move detail into the skill body, or raise the limit with a reason in scripts/context-budget.tsv.'
done

if (( failures > 0 )); then
  echo "context budget failed: $failures violation(s)" >&2
  exit 1
fi
echo "context budget passed"

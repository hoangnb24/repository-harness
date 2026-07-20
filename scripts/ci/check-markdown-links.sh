#!/usr/bin/env bash
# Check that relative Markdown links point at files that exist.
#
# Only inline links of the form [text](target) are checked. External links
# (http/https/mailto), in-page anchors (#...), and links with a #fragment are
# handled by stripping the fragment before resolving the path.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$repo_root"

status=0
checked=0

while IFS= read -r md; do
  # Pull out every ](target) target on each line.
  while IFS= read -r target; do
    [ -n "$target" ] || continue

    # Skip external and pure-anchor links.
    case "$target" in
      http://*|https://*|mailto:*|'#'*) continue ;;
    esac

    # Drop any #fragment; resolve the path relative to the file's directory.
    path="${target%%#*}"
    [ -n "$path" ] || continue

    resolved="$(dirname "$md")/$path"
    checked=$((checked + 1))

    if [ ! -e "$resolved" ]; then
      printf 'BROKEN LINK  %s -> %s\n' "$md" "$target" >&2
      status=1
    fi
  done < <(grep -oE '\]\([^)]+\)' "$md" | sed -E 's/^\]\(//; s/\)$//')
done < <(find . -name '*.md' -not -path './.git/*' | sort)

if [ "$status" -ne 0 ]; then
  printf '\nFound broken relative Markdown links.\n' >&2
elif [ "$checked" -eq 0 ]; then
  printf 'OK: no relative Markdown links to check.\n'
else
  printf 'OK: %d relative Markdown links resolve.\n' "$checked"
fi

exit "$status"

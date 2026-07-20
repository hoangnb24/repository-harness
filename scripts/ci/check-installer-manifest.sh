#!/usr/bin/env bash
# Verify that every file the installer promises to copy actually exists in the
# repo, and warn about repo files the installer forgets to copy.
#
# The installer embeds its file list in a heredoc between the two markers below.
# If someone adds or removes a Harness file but forgets to update the installer,
# this check fails.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$repo_root"

installer="scripts/install-harness.sh"

# Extract the heredoc payload: the lines between `<<'EOF'` and the closing EOF
# inside the copy loop.
manifest="$(awk "
  /done <<'EOF'/ { grab=1; next }
  grab && /^EOF\$/ { grab=0 }
  grab { print }
" "$installer")"

if [ -z "$manifest" ]; then
  echo "ERROR: could not extract the installer file manifest" >&2
  exit 1
fi

status=0

# 1. Every manifest entry must exist in the repo.
while IFS= read -r relative; do
  [ -n "$relative" ] || continue
  if [ ! -f "$relative" ]; then
    printf 'MISSING  installer lists %s but it does not exist in the repo\n' "$relative" >&2
    status=1
  fi
done <<< "$manifest"

# 2. Warn (non-fatal) about tracked Harness files the manifest never copies.
#    We only look at AGENTS.md, README.md, and docs/ — scripts/ is intentionally
#    partial (only scripts/README.md ships).
while IFS= read -r tracked; do
  case "$tracked" in
    AGENTS.md|README.md|docs/*) ;;
    *) continue ;;
  esac
  if ! grep -Fxq "$tracked" <<< "$manifest"; then
    printf 'NOTE     %s is tracked but not in the installer manifest\n' "$tracked"
  fi
done < <(git ls-files)

if [ "$status" -eq 0 ]; then
  echo "OK: installer manifest is consistent with the repo."
else
  echo "" >&2
  echo "Installer manifest is out of sync. Update the heredoc in $installer." >&2
fi

exit "$status"

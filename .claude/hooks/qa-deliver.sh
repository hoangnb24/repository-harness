#!/usr/bin/env bash
# Stop hook: when a turn ends, scan plans/reports/ for new .mp4 recordings
# (per docs/playbooks/e2e-qa-field-by-field-verify-with-report.md convention:
#  plans/reports/<feature>-<runId>.mp4 + sibling .md report) and push them
# to Telegram so the human knows "task done, here is the proof".
#
# Cache at .claude/.qa-telegram-sent keeps `path:size` keys of already-sent
# files so re-runs that produce a fresh recording (different size) get sent
# again, but unchanged ones don't repeat.

set -uo pipefail
trap 'exit 0' ERR

cwd="${CLAUDE_PROJECT_DIR:-$(pwd)}"
reports_dir="$cwd/plans/reports"
cache="$cwd/.claude/.qa-telegram-sent"
script="$cwd/.claude/scripts/telegram-send.sh"

[[ -d "$reports_dir" ]] || exit 0
[[ -x "$script" ]] || exit 0
touch "$cache" 2>/dev/null || exit 0

# Look at recordings modified in the last 30 minutes — wide enough to catch
# anything produced this session, narrow enough to skip ancient files.
mapfile -t recent < <(find "$reports_dir" -maxdepth 3 -type f -name "*.mp4" -mmin -30 2>/dev/null)
(( ${#recent[@]} > 0 )) || exit 0

LIMIT=$((50 * 1024 * 1024))

for mp4 in "${recent[@]}"; do
  size=$(stat -c %s "$mp4" 2>/dev/null || echo 0)
  (( size > 0 )) || continue

  key="${mp4}:${size}"
  if grep -qxF "$key" "$cache" 2>/dev/null; then
    continue
  fi

  stem="${mp4%.mp4}"
  name=$(basename "$stem")
  rel="${mp4#$cwd/}"

  # Companion report .md sharing the same stem, if present.
  report=""
  [[ -f "${stem}.md" ]] && report="${stem}.md"

  caption="[Task verified] ${name}
E2E recording (and report if present) attached
Path: ${rel}"

  if (( size > LIMIT )); then
    # Telegram Bot API caps at 50 MB. Send text-only notice + the report only.
    CLAUDE_PROJECT_DIR="$cwd" "$script" \
      --message "[Task verified — recording too large] ${name}
size: ${size} bytes (> 50 MB Bot API limit)
path: ${rel}
Open locally or upload manually." \
      >/dev/null 2>&1 || true
    if [[ -n "$report" ]]; then
      CLAUDE_PROJECT_DIR="$cwd" "$script" \
        --caption "Report for ${name}" \
        "$report" >/dev/null 2>&1 || true
    fi
  else
    if [[ -n "$report" ]]; then
      CLAUDE_PROJECT_DIR="$cwd" "$script" \
        --caption "$caption" \
        "$report" "$mp4" >/dev/null 2>&1 || true
    else
      CLAUDE_PROJECT_DIR="$cwd" "$script" \
        --caption "$caption" \
        "$mp4" >/dev/null 2>&1 || true
    fi
  fi

  echo "$key" >> "$cache"
done

exit 0

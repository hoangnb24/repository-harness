#!/usr/bin/env bash
# PostToolUse hook: after any Bash call, if the latest git commit is a
# stage-boundary commit (per docs/WORKFLOW.md), send the new/changed artifact
# files in that commit to Telegram so they can be reviewed by self or client.
#
# Pattern matched in commit subject: stage-<N>[a|b]   e.g. stage-3b, stage-4, stage-12
# Stage 8 (build, multi-commit cadence) is skipped to avoid spam.
#
# Delegates the actual upload to .claude/scripts/telegram-send.sh,
# which handles .env loading and 50MB-per-file Bot API limit.

set -uo pipefail
trap 'exit 0' ERR

payload=$(cat)
cmd=$(printf '%s' "$payload" | jq -r '.tool_input.command // ""')

# Fast bail: not a git commit call.
if [[ "$cmd" != *"git commit"* && "$cmd" != *"git  commit"* ]]; then
  exit 0
fi

# Resolve project dir from the session, fallback to env.
sess_cwd=$(printf '%s' "$payload" | jq -r '.cwd // ""')
[[ -d "$sess_cwd" ]] || sess_cwd="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$sess_cwd" || exit 0

# Need a git repo + at least one commit.
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

msg=$(git log -1 --pretty=%B 2>/dev/null || true)
[[ -n "$msg" ]] || exit 0
subject=$(printf '%s' "$msg" | head -n 1)

# Match stage token in the subject line.
if [[ ! "$subject" =~ stage-([0-9]{1,2}[ab]?) ]]; then
  exit 0
fi
stage="${BASH_REMATCH[1]}"

# Skip noisy / no-artifact stages.
case "$stage" in
  8|9) exit 0 ;;
esac

# Audience label per WORKFLOW.md "client review round" / "client signoff" stages.
case "$stage" in
  3b|4|6|11|12|13) audience="CLIENT review (forward to customer)" ;;
  2|3a|5|7|10)     audience="self review" ;;
  *)               audience="review" ;;
esac

# Friendly stage name.
case "$stage" in
  2)   stage_name="Intake brief" ;;
  3a)  stage_name="Discovery interview summary" ;;
  3b)  stage_name="Gap analysis (As-Is vs To-Be)" ;;
  4)   stage_name="Proposal & SOW" ;;
  5)   stage_name="Spec + Design intake" ;;
  6)   stage_name="Visual & Behavioral Modeling (prototype + diagrams)" ;;
  7)   stage_name="Story slicing" ;;
  10)  stage_name="QA + TEST_MATRIX" ;;
  11)  stage_name="UAT + signoff" ;;
  12)  stage_name="Release note + client update" ;;
  13)  stage_name="Handover + maintenance proposal" ;;
  *)   stage_name="stage ${stage}" ;;
esac

short=$(git rev-parse --short HEAD 2>/dev/null || echo "?")

# Collect files changed in HEAD that live under docs/ (artifact convention).
# Exclude STAGE.md (state tracker, not a deliverable) and obvious internal files.
mapfile -t changed < <(
  git diff-tree --no-commit-id --name-only --diff-filter=AM -r --root HEAD 2>/dev/null \
    | grep -E '^docs/' \
    | grep -v -E '(^|/)STAGE\.md$' \
    | grep -v -E '(^|/)README\.md$'
)

# Keep only existing, non-empty, under-50MB files.
files=()
LIMIT=$((50 * 1024 * 1024))
for f in "${changed[@]}"; do
  [[ -f "$f" ]] || continue
  size=$(stat -c %s "$f" 2>/dev/null || echo 0)
  (( size > 0 && size < LIMIT )) && files+=("$f")
done

# If no usable files, send a text-only notice so the human still sees the boundary.
script="$sess_cwd/.claude/scripts/telegram-send.sh"
[[ -x "$script" ]] || exit 0

if [[ ${#files[@]} -eq 0 ]]; then
  CLAUDE_PROJECT_DIR="$sess_cwd" "$script" \
    --message "[Stage ${stage} boundary] ${stage_name}
Audience: ${audience}
Commit: ${short} — ${subject}
(no docs/ files in commit to attach)" \
    >/dev/null 2>&1 || true
  exit 0
fi

caption="[Stage ${stage}] ${stage_name}
Audience: ${audience}
Commit: ${short} — ${subject}
Files: ${#files[@]}"

CLAUDE_PROJECT_DIR="$sess_cwd" "$script" \
  --caption "$caption" \
  "${files[@]}" \
  >/dev/null 2>&1 || true

exit 0

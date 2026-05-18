#!/usr/bin/env bash
# Send files to Telegram as Documents (preserves originals, no re-encoding).
#
# Usage:
#   telegram-send.sh [--caption "text"] [--chat-id ID] file1 [file2 ...]
#   telegram-send.sh --message "text only, no files"
#
# Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from $CLAUDE_PROJECT_DIR/.claude/.env
# or the shell environment. Bot API limit: 50MB per file.

set -uo pipefail

CAPTION=""
MESSAGE=""
OVERRIDE_CHAT_ID=""
files=()

usage() {
  cat <<EOF
Usage: $(basename "$0") [options] file [file ...]

Options:
  -c, --caption TEXT     Caption applied to the FIRST file only.
  -m, --message TEXT     Send a text-only message (no files needed).
  --chat-id ID           Override TELEGRAM_CHAT_ID for this call.
  -h, --help             Show this help.

Examples:
  $(basename "$0") --caption "Stage 4 deliverables" dist/*.zip docs/*.pdf
  $(basename "$0") --message "Stage 4 complete, files incoming"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--caption)  CAPTION="${2:-}"; shift 2 ;;
    -m|--message)  MESSAGE="${2:-}"; shift 2 ;;
    --chat-id)     OVERRIDE_CHAT_ID="${2:-}"; shift 2 ;;
    -h|--help)     usage; exit 0 ;;
    --)            shift; while [[ $# -gt 0 ]]; do files+=("$1"); shift; done ;;
    -*)            echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)             files+=("$1"); shift ;;
  esac
done

# Load creds from project .env (shell env wins via set -a precedence).
env_file="${CLAUDE_PROJECT_DIR:-$(pwd)}/.claude/.env"
if [[ -f "$env_file" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$env_file"
  set +a
fi

: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN not set (check .claude/.env)}"
CHAT_ID="${OVERRIDE_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
: "${CHAT_ID:?TELEGRAM_CHAT_ID not set (check .claude/.env or pass --chat-id)}"

api="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"

# Text-only mode
if [[ -n "$MESSAGE" && ${#files[@]} -eq 0 ]]; then
  resp=$(curl -sS -m 15 -X POST "${api}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}")
  ok=$(printf '%s' "$resp" | jq -r '.ok // false')
  if [[ "$ok" == "true" ]]; then
    echo "sent message (msg_id=$(printf '%s' "$resp" | jq -r '.result.message_id'))"
    exit 0
  fi
  echo "fail: $(printf '%s' "$resp" | jq -r '.description // "unknown"')" >&2
  exit 1
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "error: no files given. Use --message for text-only, or pass file paths." >&2
  usage >&2
  exit 2
fi

# Optional preface message if caption provided alongside files.
if [[ -n "$MESSAGE" ]]; then
  curl -sS -m 15 -X POST "${api}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}" > /dev/null || true
fi

LIMIT_BYTES=$((50 * 1024 * 1024))
# Pacing: small delay between sends keeps us well under Telegram per-chat limits
# (~1 msg/sec to same chat). Override with TELEGRAM_SEND_DELAY (seconds, can be 0).
SEND_DELAY="${TELEGRAM_SEND_DELAY:-0.4}"
fail=0
first=1
sent_count=0

send_one() {
  # $1=file, $2=size; respects $CAPTION + $first; retries once on HTTP 429.
  local f="$1" size="$2" attempt resp ok err retry
  local args=(-sS -m 300 -X POST "${api}/sendDocument"
              -F "chat_id=${CHAT_ID}"
              -F "document=@${f}")
  if [[ $first -eq 1 && -n "$CAPTION" ]]; then
    args+=(-F "caption=${CAPTION}")
    first=0
  fi

  for attempt in 1 2; do
    resp=$(curl "${args[@]}")
    ok=$(printf '%s' "$resp" | jq -r '.ok // false')
    if [[ "$ok" == "true" ]]; then
      local msgid
      msgid=$(printf '%s' "$resp" | jq -r '.result.message_id')
      echo "sent: $f (msg_id=$msgid, ${size} bytes)"
      sent_count=$((sent_count + 1))
      return 0
    fi
    # Honor Telegram's retry_after on 429.
    retry=$(printf '%s' "$resp" | jq -r '.parameters.retry_after // empty')
    if [[ -n "$retry" && $attempt -eq 1 ]]; then
      echo "rate-limited, sleeping ${retry}s then retry: $f" >&2
      sleep "$retry"
      continue
    fi
    err=$(printf '%s' "$resp" | jq -r '.description // "unknown error"')
    echo "fail: $f -- $err" >&2
    fail=1
    return 1
  done
}

i=0
for f in "${files[@]}"; do
  i=$((i + 1))
  if [[ ! -f "$f" ]]; then
    echo "skip (not a file): $f" >&2
    fail=1
    continue
  fi
  size=$(stat -c %s "$f" 2>/dev/null || stat -f %z "$f")
  if [[ "$size" -gt "$LIMIT_BYTES" ]]; then
    echo "skip (>50MB Bot API limit, size=${size}): $f" >&2
    fail=1
    continue
  fi

  send_one "$f" "$size" || true

  # Pace between sends (skip after last file).
  if (( i < ${#files[@]} )); then
    sleep "$SEND_DELAY" 2>/dev/null || true
  fi
done

echo "done: ${sent_count}/${#files[@]} sent"
exit "$fail"

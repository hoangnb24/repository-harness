#!/usr/bin/env bash
# Telegram notifier for Claude Code hooks.
# Reads the hook event JSON from stdin and pushes a short message to Telegram.
# Required env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# Optional env: TELEGRAM_NOTIFY_SILENT=1 (sends with disable_notification=true)

set -uo pipefail

# Never block Claude Code: any failure here exits 0 so the hook stays non-fatal.
trap 'exit 0' ERR

# Auto-load .claude/.env if present (env vars from shell still win — set -a + source
# only assigns vars that aren't already exported).
env_file="${CLAUDE_PROJECT_DIR:-$(pwd)}/.claude/.env"
if [[ -f "$env_file" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  exit 0
fi

payload=$(cat)
event=$(printf '%s' "$payload" | jq -r '.hook_event_name // "unknown"')
cwd=$(printf '%s' "$payload" | jq -r '.cwd // "?"')
session=$(printf '%s' "$payload" | jq -r '.session_id // "?"' | cut -c1-8)
host=$(hostname -s 2>/dev/null || echo "host")

case "$event" in
  Notification)
    msg=$(printf '%s' "$payload" | jq -r '.message // "(no message)"')
    text="[Claude] needs attention
host: ${host}
session: ${session}
dir: ${cwd}

${msg}"
    ;;
  Stop)
    # Try to grab the last assistant text from the transcript for context.
    tpath=$(printf '%s' "$payload" | jq -r '.transcript_path // ""')
    last=""
    if [[ -n "$tpath" && -f "$tpath" ]]; then
      last=$(tac "$tpath" 2>/dev/null \
        | jq -rR 'fromjson? | select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text' 2>/dev/null \
        | head -n 1 \
        | cut -c1-300)
    fi
    text="[Claude] turn finished
host: ${host}
session: ${session}
dir: ${cwd}"
    if [[ -n "$last" ]]; then
      text="${text}

last: ${last}"
    fi
    ;;
  *)
    text="[Claude] event: ${event}
host: ${host}
session: ${session}
dir: ${cwd}"
    ;;
esac

disable_notif="false"
[[ "${TELEGRAM_NOTIFY_SILENT:-0}" == "1" ]] && disable_notif="true"

curl -fsS -m 5 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${text}" \
  --data-urlencode "disable_notification=${disable_notif}" \
  > /dev/null 2>&1 || true

exit 0

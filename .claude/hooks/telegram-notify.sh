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
    # Pull the most recent assistant message in full so we can scan it for
    # the MANUAL_CHECKPOINT convention (a richer signal than the generic
    # "turn finished" — used when Claude hands off to the human for offline
    # work like opening claude.ai/design, reviewing a SOW, etc.).
    #
    # Convention (write this in the assistant turn that ends with manual handoff):
    #   MANUAL_CHECKPOINT: <one-line what the human must do>
    #   <optional follow-up lines: URLs, return condition>
    #   <blank line ends the block>
    tpath=$(printf '%s' "$payload" | jq -r '.transcript_path // ""')
    last_full=""
    if [[ -n "$tpath" && -f "$tpath" ]]; then
      last_json=$(tac "$tpath" 2>/dev/null | while IFS= read -r ln; do
        if printf '%s' "$ln" | jq -e '.type=="assistant"' >/dev/null 2>&1; then
          printf '%s' "$ln"
          break
        fi
      done)
      if [[ -n "$last_json" ]]; then
        last_full=$(printf '%s' "$last_json" \
          | jq -r '.message.content // [] | map(select(.type=="text") | .text) | join("\n\n")' 2>/dev/null)
      fi
    fi

    if [[ -n "$last_full" ]] && printf '%s' "$last_full" | grep -q 'MANUAL_CHECKPOINT'; then
      # Capture from the first MANUAL_CHECKPOINT line to end of assistant text.
      # Blocks separated by blank lines stay together; trailing prose is
      # included (it usually clarifies what the human should do next).
      block=$(printf '%s' "$last_full" | awk '/MANUAL_CHECKPOINT/{p=1} p{print}' | head -c 3500)
      text="[MANUAL CHECKPOINT] Claude is waiting on offline work
host: ${host}
session: ${session}
dir: ${cwd}

${block}"
    else
      last_line=$(printf '%s' "$last_full" | head -n 1 | cut -c1-300)
      text="[Claude] turn finished
host: ${host}
session: ${session}
dir: ${cwd}"
      if [[ -n "$last_line" ]]; then
        text="${text}

last: ${last_line}"
      fi
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

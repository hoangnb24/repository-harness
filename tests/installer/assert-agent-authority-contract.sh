#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
agent_block="$root/scripts/agent-harness-block.md"
claude_block="$root/scripts/claude-harness-block.md"

extract_block() {
  awk '
    /<!-- HARNESS:BEGIN -->/ { in_block = 1 }
    in_block { print }
    /<!-- HARNESS:END -->/ { exit }
  ' "$1"
}

cmp -s <(extract_block "$root/AGENTS.md") "$agent_block"
cmp -s <(extract_block "$root/CLAUDE.md") "$claude_block"

grep -Fq 'answer, explanation, review, diagnosis' "$agent_block"
grep -Fq 'task read-only' "$agent_block"
grep -Fq 'Do not bootstrap' "$agent_block"
grep -Fq 'change, build, fix, or write repository' "$agent_block"
grep -Fq 'scripts/bootstrap-harness.sh' "$agent_block"
grep -Fq 'query matrix --active --summary' "$agent_block"
grep -Fq 'lane- and task-specific context' "$agent_block"
! grep -Fq 'Before work, read:' "$agent_block"
[[ "$(wc -c <"$agent_block" | tr -d ' ')" -le 1600 ]]
tiny_change_bytes=$(($(wc -c <"$agent_block") + $(wc -c <"$root/docs/FEATURE_INTAKE.md") + 1024))
tiny_change_words=$(($(wc -w <"$agent_block") + $(wc -w <"$root/docs/FEATURE_INTAKE.md") + 120))
[[ "$tiny_change_bytes" -le 8192 ]]
[[ "$tiny_change_words" -le 1200 ]]

[[ "$(grep -Fc '@AGENTS.md' "$claude_block")" == 1 ]]
! grep -Fq '@docs/FEATURE_INTAKE.md' "$claude_block"
! grep -Fq 'query matrix' "$claude_block"

grep -Fxq 'scripts/agent-harness-block.md' "$root/scripts/harness-install-files.txt"
grep -Fxq 'scripts/claude-harness-block.md' "$root/scripts/harness-install-files.txt"
grep -Fq 'read_source_text "scripts/agent-harness-block.md"' "$root/scripts/install-harness.sh"
grep -Fq 'read_source_text "scripts/claude-harness-block.md"' "$root/scripts/install-harness.sh"
grep -Fq 'REFRESH_AGENT_SHIM=1' "$root/scripts/install-harness.sh"
! grep -Fq "cat <<'EOF'" <(sed -n '/agent_shim_block()/,/^}/p' "$root/scripts/install-harness.sh")

# PowerShell is asserted statically on hosts without pwsh. Runtime coverage is
# provided by test-install-harness-modes.ps1 in the Windows release job.
grep -Fq 'Read-SourceText "scripts/agent-harness-block.md"' "$root/scripts/install-harness.ps1"
grep -Fq '$RefreshAgentShim = $true' "$root/scripts/install-harness.ps1"
grep -Fq 'Assert-HarnessMarkers $content "AGENTS.md"' "$root/scripts/install-harness.ps1"
! grep -Fq '<!-- HARNESS:BEGIN -->' <(sed -n '/function Get-AgentShimBlock/,/^}/p' "$root/scripts/install-harness.ps1")

echo "Agent authority, bounded context, canonical shims, and installer parity contracts passed"

#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
agent_block="$root/scripts/agent-harness-block.md"
claude_block="$root/scripts/claude-harness-block.md"
workflow="$root/docs/WORKFLOW.md"

extract_block() {
  awk '
    /<!-- HARNESS:BEGIN -->/ { in_block = 1 }
    in_block { print }
    /<!-- HARNESS:END -->/ { exit }
  ' "$1"
}

cmp -s <(extract_block "$root/AGENTS.md") "$agent_block"
cmp -s <(extract_block "$root/CLAUDE.md") "$claude_block"

grep -Fq 'Start with the requested outcome' "$agent_block"
grep -Fq 'Answers, explanations, reviews, diagnoses, plans, and status reports are' "$agent_block"
grep -Fq 'No Harness CLI operation is required.' "$agent_block"
grep -Fq 'docs/plans/active/' "$agent_block"
grep -Fq 'Pause when product intent is ambiguous' "$agent_block"
grep -Fq 'SQLite intake, story, trace, scoring, audit, and proposal commands are optional' "$agent_block"
! grep -Fq 'scripts/bootstrap-harness.sh' "$agent_block"
! grep -Fq 'query matrix --active --summary' "$agent_block"
! grep -Fq 'lane- and task-specific context' "$agent_block"
[[ "$(wc -c <"$agent_block" | tr -d ' ')" -le 1600 ]]

# The only mandatory initial Harness context stays near the approximately
# 1,000-word target. Everything else is retrieved because the task needs it.
entry_words=$(awk '{ words += NF } END { print words }' "$root/AGENTS.md" "$workflow")
[[ "$entry_words" -le 1000 ]]

grep -Fq 'Does The Work Need Durable Memory?' "$workflow"
grep -Fq 'Does The Work Need Human Judgment?' "$workflow"
grep -Fq 'What Proves The Behavior?' "$workflow"
grep -Fq 'No bootstrap, intake, story, matrix, trace, scoring, audit, or proposal command' "$workflow"
grep -Fq 'ordinary repository task' "$root/docs/HARNESS.md"

[[ "$(grep -Fc '@AGENTS.md' "$claude_block")" == 1 ]]
! grep -Fq '@docs/FEATURE_INTAKE.md' "$claude_block"
! grep -Fq 'query matrix' "$claude_block"

for payload in \
  docs/WORKFLOW.md \
  docs/plans/README.md \
  docs/plans/active/README.md \
  docs/plans/completed/README.md \
  docs/templates/exec-plan.md \
  scripts/agent-harness-block.md \
  scripts/claude-harness-block.md; do
  grep -Fxq "$payload" "$root/scripts/harness-install-files.txt"
done

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

echo "repository-centered authority, bounded context, canonical shims, and installer parity passed"

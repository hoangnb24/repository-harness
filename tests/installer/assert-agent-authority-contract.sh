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

required_agent_text=(
  'Start with the requested outcome'
  'Inspection does not authorize edits or operation.'
  'missing capabilities'
  'configurable defaults are not authority'
  "repository's native safety and validation"
  'Only invoke a Harness skill when the user explicitly requests it.'
  'Consumer repositories own their task workflow and planning.'
)
for text in "${required_agent_text[@]}"; do
  grep -Fq "$text" "$agent_block"
done
! grep -Fq 'docs/plans/active/' "$agent_block"
! grep -Fq 'docs/patterns/encoding-invariants.md' "$agent_block"

# Entry size and word limits live in scripts/context-budget.tsv.
"$root/scripts/check-context-budget.sh" >/dev/null

required_workflow_text=(
  '## Authority And Scope'
  'stop and request the smallest'
  '## Missing Capabilities'
  'Keep unobserved state Unknown.'
  '## Trust Through Evidence'
  'structural checks from semantic or runtime proof'
  'Only invoke a Harness skill when the user explicitly requests it.'
)
for text in "${required_workflow_text[@]}"; do
  grep -Fq "$text" "$workflow"
done
! grep -Fq 'Select The Work Shape' "$workflow"
! grep -Fq '### Bounded Change' "$workflow"

[[ "$(grep -Fc '@AGENTS.md' "$claude_block")" == 1 ]]
! grep -Fq 'query matrix' "$claude_block"

payloads=(
  .agents/skills/audit-onboarding-proposal/SKILL.md
  .agents/skills/audit-onboarding-proposal/agents/openai.yaml
  .agents/skills/audit-onboarding-proposal/scripts/validate_evidence_capsule.py
  .agents/skills/encode-invariant/SKILL.md
  .agents/skills/encode-invariant/agents/openai.yaml
  .agents/skills/improve-harness/SKILL.md
  .agents/skills/improve-harness/agents/openai.yaml
  .agents/skills/onboard-repository/SKILL.md
  .agents/skills/onboard-repository/agents/openai.yaml
  .agents/skills/onboard-repository/references/evidence-capsule-v1.md
  .agents/skills/onboard-repository/references/evidence-capsule-v2.md
  .agents/skills/onboard-repository/scripts/emit_evidence_bundle.py
  .agents/skills/onboard-repository/scripts/render_patch.py
  docs/WORKFLOW.md
  docs/README.md
  docs/patterns/encoding-invariants.md
  docs/product/README.md
  docs/plans/README.md
  docs/plans/active/README.md
  docs/plans/completed/README.md
  docs/decisions/README.md
  docs/templates/application-runbook.md
  docs/templates/decision.md
  docs/templates/exec-plan.md
  docs/templates/harness-improvement.md
)
for payload in "${payloads[@]}"; do
  grep -Fxq "$payload" "$root/scripts/harness-install-files.txt"
done

# Source/configuration contract only: host activation and agent compliance
# require separate runtime evidence. Cover every skill declared by either profile.
while IFS= read -r metadata; do
  case "$metadata" in
    .agents/skills/*/agents/openai.yaml)
      grep -Fq 'allow_implicit_invocation: false' "$root/$metadata"
      ! grep -Fq 'allow_implicit_invocation: true' "$root/$metadata"
      skill="${metadata%/agents/openai.yaml}/SKILL.md"
      grep -Fq 'Use only when the user explicitly invokes' "$root/$skill"
      ;;
  esac
done < <(cat "$root/scripts/harness-install-files.txt" "$root/scripts/engineering-wisdom-install-files.txt")

invariant_skill="$root/.agents/skills/encode-invariant/SKILL.md"
grep -Fq 'Do not infer policy from conventions, code patterns, tests, defaults, or undocumented preferences.' \
  "$invariant_skill"
required_invariant_method=(
  "Reuse the repository's existing test, build, task, lint, scan, or validation"
  'Choose the lowest deterministic layer that sees the complete accepted'
  'name the violating item, the broken rule, the'
  'authority source, and a concrete compliant next action'
  'local validation command and observed result'
  'optional hook availability, if any'
  'CI invocation discovered or absent'
  'branch-protection enforcement verified or unverified'
)
for text in "${required_invariant_method[@]}"; do
  grep -Fq "$text" "$invariant_skill"
done

onboarding_skill="$root/.agents/skills/onboard-repository/SKILL.md"
grep -Fq 'Compare documented invariants with executable checks' "$onboarding_skill"
grep -Fq '**Unenforced rule:**' "$onboarding_skill"
grep -Fq '**Check lacking authority:**' "$onboarding_skill"
grep -Fq 'Do not add, edit, delete, enable, or execute a guard during onboarding.' \
  "$onboarding_skill"

grep -Fq 'read_source_text "scripts/agent-harness-block.md"' "$root/scripts/install-harness.sh"
grep -Fq 'read_source_text "scripts/claude-harness-block.md"' "$root/scripts/install-harness.sh"
grep -Fq 'REFRESH_AGENT_SHIM=1' "$root/scripts/install-harness.sh"
grep -Fq 'ENGINEERING_WISDOM_PAYLOAD_MANIFEST="scripts/engineering-wisdom-install-files.txt"' "$root/scripts/install-harness.sh"
! grep -Fq 'CLI_PAYLOAD_MANIFEST' "$root/scripts/install-harness.sh"

grep -Fq 'Read-SourceText "scripts/agent-harness-block.md"' "$root/scripts/install-harness.ps1"
grep -Fq '[switch]$RefreshAgentShim' "$root/scripts/install-harness.ps1"
grep -Fq '$script:EngineeringWisdomPayloadManifest = "scripts/engineering-wisdom-install-files.txt"' "$root/scripts/install-harness.ps1"
! grep -Fq 'CliPayloadManifest' "$root/scripts/install-harness.ps1"

echo "repository authority, explicit skill configuration, canonical shims, and installer parity passed"

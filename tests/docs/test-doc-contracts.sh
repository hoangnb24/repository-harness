#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  printf 'documentation contract failed: %s\n' "$*" >&2
  exit 1
}

require() {
  local file=$1
  local text=$2
  rg -Fq -- "$text" "$root/$file" || fail "$file omits: $text"
}

reject() {
  local file=$1
  local text=$2
  if rg -Fq -- "$text" "$root/$file"; then
    fail "$file contains stale default-path instruction: $text"
  fi
}

# Current default authority is repository-centered and explicitly keeps
# workflow-database operations off the bounded path.
require AGENTS.md 'Start with the requested outcome'
require AGENTS.md 'No control-plane operation is required.'
require docs/WORKFLOW.md '### Bounded Change'
require docs/WORKFLOW.md '### Durable Planned Change'
require docs/WORKFLOW.md '### Does The Work Need Human Judgment?'
require docs/WORKFLOW.md '### Operate The Application'
require docs/WORKFLOW.md '### Improve The Harness'
require AGENTS.md 'configurable defaults are not authority'
require AGENTS.md 'explicitly asked to use `$improve-harness`'
require docs/WORKFLOW.md '`Add rate limiting` without a quota'
require docs/WORKFLOW.md 'must stop'
require docs/HARNESS.md 'ordinary repository task'
require docs/CONTEXT_RULES.md 'The mandatory entry context is `AGENTS.md` plus `docs/WORKFLOW.md`'
require README.md 'The default path requires no local database.'
require docs/demo/README.md '## 4. Consequential Ambiguity'

for file in AGENTS.md docs/WORKFLOW.md docs/HARNESS.md docs/CONTEXT_RULES.md; do
  reject "$file" 'scripts/bin/harness-cli query matrix --active --summary'
  reject "$file" 'first run `scripts/bootstrap-harness.sh`'
done

# Durable planning and decision structure are part of both source and the
# fresh core. Upstream decisions remain source-only.
for file in \
  .agents/skills/audit-onboarding-proposal/SKILL.md \
  .agents/skills/audit-onboarding-proposal/agents/openai.yaml \
  .agents/skills/audit-onboarding-proposal/scripts/validate_evidence_capsule.py \
  .agents/skills/improve-harness/SKILL.md \
  .agents/skills/improve-harness/agents/openai.yaml \
  .agents/skills/onboard-repository/SKILL.md \
  .agents/skills/onboard-repository/agents/openai.yaml \
  .agents/skills/onboard-repository/references/evidence-capsule-v1.md \
  .agents/skills/onboard-repository/references/evidence-capsule-v2.md \
  .agents/skills/onboard-repository/scripts/emit_evidence_bundle.py \
  .agents/skills/onboard-repository/scripts/render_patch.py \
  docs/README.md \
  docs/product/README.md \
  docs/plans/README.md \
  docs/plans/active/README.md \
  docs/plans/completed/README.md \
  docs/decisions/README.md \
  docs/templates/application-runbook.md \
  docs/templates/decision.md \
  docs/templates/exec-plan.md \
  docs/templates/harness-improvement.md; do
  [[ -f "$root/$file" ]] || fail "missing repository artifact: $file"
  grep -Fxq "$file" "$root/scripts/harness-install-files.txt" ||
    fail "installer payload omits: $file"
done
for file in \
  docs/decisions/0019-repository-centered-default-workflow.md \
  docs/decisions/0020-installation-profiles-and-knowledge-boundaries.md \
  docs/decisions/0021-consumer-first-application-legibility-phase.md \
  docs/decisions/0022-control-plane-freeze-and-compatibility-runway.md \
  docs/decisions/0023-optional-consumer-ownership.md \
  docs/decisions/0024-rust-harness-core-maintenance-cli.md \
  docs/compatibility/README.md \
  docs/provenance/README.md; do
  [[ -f "$root/$file" ]] || fail "missing source-only artifact: $file"
done

for heading in Outcome Context Scope Approach 'Risks And Recovery' Progress Decisions Validation Result; do
  require docs/templates/exec-plan.md "## $heading"
done
for heading in Scope Prerequisites Start Readiness 'Deterministic State' Interface \
  'Runtime Evidence' 'Ownership And Cleanup' Validation Unknowns; do
  require docs/templates/application-runbook.md "## $heading"
done
for heading in Status 'Representative Job' Baseline 'Earliest Gap' \
  'Correct Owner' Intervention 'Native Validation' 'Fresh Rerun' Decision Result; do
  require docs/templates/harness-improvement.md "## $heading"
done
require .agents/skills/improve-harness/agents/openai.yaml \
  'allow_implicit_invocation: false'

# Old surfaces remain available but must identify themselves as compatibility
# references before presenting commands or lifecycle policy.
for file in \
  docs/FEATURE_INTAKE.md \
  docs/TEST_MATRIX.md \
  docs/TRACE_SPEC.md \
  docs/HARNESS_AUDIT.md \
  docs/HARNESS_MATURITY.md \
  docs/HARNESS_BACKLOG.md \
  docs/IMPROVEMENT_PROTOCOL.md \
  docs/TOOL_REGISTRY.md \
  docs/stories/README.md; do
  head -n 12 "$root/$file" | rg -Fq 'Compatibility' ||
    fail "$file lacks an early compatibility boundary"
  grep -Fxq "$file" "$root/scripts/harness-cli-install-files.txt" ||
    fail "CLI compatibility payload omits: $file"
done

require scripts/README.md 'Normal'
require scripts/README.md 'story row, matrix query, trace, score, audit, or proposal'
require docs/ARCHITECTURE.md 'The upstream Harness product is a Rust workspace with two independent binaries.'
require docs/ARCHITECTURE.md '`crates/harness/` is the default core-maintenance CLI.'
require docs/ARCHITECTURE.md 'The reusable template does not select an application stack'
require scripts/README.md 'Installed consumer projects keep their own stack-specific validation commands'
require scripts/README.md 'By default the installer downloads the checksum-verified `harness` maintenance'
require docs/README.md '## Installed Core'
require docs/README.md '## Source-Repository Indexes'
require tests/README.md '## Current Core'
require tests/README.md '## Optional Compatibility CLI'
require tests/README.md '## Historical Migration Proof'
require docs/compatibility/README.md '## Install Boundary'
require docs/plans/active/application-legibility.md '# Execution Plan: Application Legibility Pilot'
require docs/plans/active/application-legibility.md '## Evidence Matrix'
require docs/plans/active/application-legibility.md '## What Remains To Prove'
require docs/plans/active/application-legibility.md 'Phase 3 completes only when one task exercises that loop'
require docs/decisions/README.md '0021-consumer-first-application-legibility-phase.md'
require docs/decisions/0021-consumer-first-application-legibility-phase.md 'Phase 3 therefore remains active.'
require docs/plans/README.md 'application-legibility.md'
require docs/plans/completed/README.md 'rust-harness-core-maintenance-cli.md'
require docs/plans/completed/README.md 'repository-cleanup.md'
require docs/plans/completed/repository-cleanup.md 'Completed. Current application-legibility work now lives'
require docs/plans/completed/rust-harness-core-maintenance-cli.md 'A Rust executable named `harness`.'
require docs/plans/completed/rust-harness-core-maintenance-cli.md 'optional SQLite control plane remains outside the CLI'
require docs/plans/completed/rust-harness-core-maintenance-cli.md 'PR #56'
require docs/plans/completed/README.md 'phase-4-control-plane-freeze.md'
require docs/plans/completed/phase-4-control-plane-freeze.md 'Complete. New upstream work has one Git-native authority path.'
require docs/plans/completed/phase-4-control-plane-freeze.md '## Validation'
require docs/decisions/README.md '0022-control-plane-freeze-and-compatibility-runway.md'
require docs/decisions/0022-control-plane-freeze-and-compatibility-runway.md 'warn on new upstream legacy lifecycle writes'
require docs/compatibility/README.md 'phase-4-write-consumer-inventory.md'
require docs/compatibility/phase-4-write-consumer-inventory.md 'No current upstream product or execution authority exists only in SQLite.'
require docs/contracts/harness-orchestration-v1.md '`--compatibility-write` flag'
require scripts/README.md '`--compatibility-write` flag'
require docs/compatibility/phase-3-active-observability-legacy.md 'Historical compatibility plan.'
require docs/compatibility/phase-4-mechanical-verification-legacy.md 'Historical compatibility roadmap.'
require docs/provenance/README.md 'source evidence, not default task'
require docs/decisions/README.md '0023-optional-consumer-ownership.md'
require docs/decisions/0023-optional-consumer-ownership.md '`hoangnb24/symphony` owns orchestration policy'
require docs/decisions/README.md '0024-rust-harness-core-maintenance-cli.md'
require docs/decisions/0024-rust-harness-core-maintenance-cli.md 'The next upstream product goal is a Rust CLI named `harness`.'
require docs/decisions/README.md '0025-latest-release-self-update-and-human-directed-conflicts.md'
require docs/decisions/0025-latest-release-self-update-and-human-directed-conflicts.md '`harness update --continue --dry-run`'
require docs/product/installation-profiles.md '.harness-core/update/'
require README.md 'scripts/bin/harness update --continue'
require README.md 'Symphony owns work selection, agent runs, worktrees'
require docs/compatibility/README.md 'Phase 5 ownership boundary'
require docs/compatibility/README.md 'phase-5-evolution-infrastructure-legacy.md'
require docs/compatibility/phase-5-evolution-infrastructure-legacy.md 'Historical compatibility roadmap.'
require docs/plans/completed/README.md 'phase-5-optional-consumer-split.md'
require docs/plans/completed/phase-5-optional-consumer-split.md 'Complete. Symphony remains the independent owner'

for executable in \
  scripts/validate-premerge.sh \
  scripts/verify-revision-coherence.sh \
  tests/boundary/test-phase5-optional-consumer-split.sh \
  tests/workflow/test-repository-workflow.sh \
  tests/workflow/test-task-authority.sh; do
  [[ -x "$root/$executable" ]] || fail "documented gate is not executable: $executable"
done

for required_gate in \
  'cargo fmt --all -- --check' \
  'cargo test --workspace --locked' \
  'cargo clippy --workspace --all-targets --locked -- -D warnings' \
  'scripts/verify-revision-coherence.sh' \
  'tests/boundary/test-phase4-control-plane-freeze.sh' \
  'tests/boundary/test-phase5-optional-consumer-split.sh' \
  'tests/docs/test-doc-contracts.sh' \
  'tests/workflow/test-repository-workflow.sh' \
  'tests/workflow/test-task-authority.sh' \
  'tests/maintenance/test-harness-release-classification.sh' \
  'tests/release/test-harness-release-workflow-contract.sh' \
  'tests/release/test-harness-release-identity-guard.sh' \
  'tests/release/test-post-merge-release-recovery.sh'; do
  require scripts/validate-premerge.sh "$required_gate"
done

"$root/tests/installer/assert-agent-authority-contract.sh" >/dev/null
"$root/tests/installer/assert-install-manifest-links.sh" >/dev/null

require .github/workflows/premerge.yml 'run: scripts/validate-premerge.sh'
rg -Fq 'tests/installer/test-install-harness-modes.ps1' "$root/.github/workflows/premerge.yml" &&
  rg -Fq -- '-InitialArtifact dist/us092-harness-cli-windows-x64.exe' \
    "$root/.github/workflows/premerge.yml" ||
  fail 'pull-request workflow does not exercise the PowerShell installer contract'
require .github/workflows/harness-cli-release.yml 'run: scripts/validate-premerge.sh'
require .github/workflows/harness-release.yml 'run: scripts/validate-premerge.sh'

echo "repository workflow, compatibility boundary, links, authority, and validation references passed"

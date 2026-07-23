# 0026 Explicit Onboarding Skills In Default Core

Date: 2026-07-23

## Status

Accepted and active.

## Context

Decisions 0020 and 0023 kept the default installation small and excluded
generic evaluation machinery. Application-legibility work then tested an
explicit, repository-owned onboarding workflow against the brownfield
`e-inna-brain` consumer.

The pilot produced two forward-tested skills:

- `$onboard-repository` maps one real repository path, remains read-only on its
  first pass, and emits evidence-backed proposals; and
- `$audit-onboarding-proposal` independently checks the producer transcript and
  exact proposed patches before application.

The frozen replay showed a direct improvement: replacing a stale installed
instruction removed one obsolete command attempt. It also showed why the
guardrails belong with the workflow: incomplete preflight, ownership omissions,
and unsupported runtime claims remained visible rather than being promoted as
product truth.

Keeping the skills only in a consumer experiment makes the learned workflow
unavailable to the next installed repository. Auto-running them, however,
would add hidden startup work and could inspect or propose changes when the
user did not request onboarding.

## Decision

1. The default Harness core installs both skills under `.agents/skills/`.
2. Both skills remain explicit-only through
   `allow_implicit_invocation: false`. Installation does not invoke them and
   does not create a first-run hook.
3. `$onboard-repository` is the user-facing entry point. Its first pass is
   inspection and proposal only; repository edits require exact user approval.
4. `$audit-onboarding-proposal` is the independent verification companion. It
   remains read-only and does not grant approval by itself.
5. Their scripts and references are managed core files because they provide
   deterministic patch rendering, evidence transport, and validation for the
   two skills. They do not become mandatory steps for ordinary repository work.
6. The skills may use Python when explicitly invoked. Core installation,
   updates, and ordinary work do not require Python. A missing runtime
   prerequisite must stop the invoked skill safely rather than trigger an
   installer-side dependency installation.
7. This decision narrowly amends decisions 0020 and 0023. The installer still
   has exactly two profiles, and the default core still excludes generic
   benchmarks, trace scoring, orchestrators, application adapters, databases,
   and the compatibility control plane.

## Alternatives Considered

1. **Keep the skills only in the pilot consumer.** Rejected because validated
   onboarding behavior would not reach newly installed repositories.
2. **Auto-run onboarding after installation.** Rejected because installation
   cannot determine whether a repository is ready for inspection, which
   operational path the user wants mapped, or whether the current agent owns
   the necessary runtime state.
3. **Add a third installer profile.** Rejected because the skills are generic
   repository workflow guidance, while another profile would recreate the
   feature-matrix problem rejected by decision 0020.
4. **Install only the producer skill.** Rejected because the pilot repeatedly
   found plausible but unsupported proposal clauses that required an
   independent fail-closed audit.
5. **Remove deterministic scripts before promotion.** Rejected because exact
   patch rendering and authenticated evidence transport fixed observed
   transcription and incomplete-preimage failures.

## Consequences

Positive:

- A fresh Harness installation exposes a tested brownfield onboarding path.
- The first pass remains safe and approval-gated.
- Installed skills and their deterministic resources update through the same
  provenance-aware merge as the rest of the core.
- Ordinary tasks retain the compact `AGENTS.md` plus `docs/WORKFLOW.md` entry
  context because neither skill is implicitly invoked.

Tradeoffs:

- The default managed payload grows by two skills and seven bundled resources.
- Explicit onboarding currently needs Python for deterministic rendering and
  validation.
- Consumer edits to managed skill files can produce normal three-way update
  conflicts.
- The evidence protocol is more complex than the ordinary task workflow and
  must remain isolated until explicitly invoked.

## Follow-Up

- Keep both skill packages valid under `quick_validate.py`.
- Exercise fresh and merge installation on Bash and PowerShell.
- Treat further simplification as a measured skill revision, not an untested
  rewrite during packaging.

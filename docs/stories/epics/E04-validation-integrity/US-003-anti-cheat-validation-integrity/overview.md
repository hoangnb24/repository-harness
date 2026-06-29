# Overview

## Current Behavior

Harness records proof and traces, but agents can still change validation,
tests, CI rules, or policy surfaces in the same work that they are trying to
pass.

## Target Behavior

Harness defines validation integrity as a protected anti-cheat layer. Protected
surfaces require owner review and decision records, and a mechanical script can
reject unreviewed policy/test/proof changes.

## Affected Users

- Humans reviewing agent work.
- Agents implementing normal and high-risk stories.
- CI or future automation validating merge readiness.

## Affected Product Docs

- `docs/VALIDATION_INTEGRITY.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/GIT_WORKFLOW.md`
- `docs/TRACE_SPEC.md`
- `.github/CODEOWNERS`
- `.github/pull_request_template.md`
- `.github/workflows/harness-validation.yml`

## Non-Goals

- Add application-specific tests before an application stack exists.
- Enforce remote branch protection locally.
- Make Harness traces tamper-proof in this story.

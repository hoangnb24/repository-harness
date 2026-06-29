# Exec Plan

## Goal

Add anti-cheat controls that make validation, test, CI, trace, and protected
policy changes visible and mechanically checkable.

## Scope

In scope:

- Validation integrity policy.
- Protected file list.
- CODEOWNERS template.
- Pull request template.
- GitHub Actions workflow.
- Local validation integrity script.
- Harness doc links and story proof.

Out of scope:

- Stack-specific application tests.
- Remote branch protection configuration.
- Append-only external trace storage.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- Removing or weakening validation requirements.
- Changing validation requirements.
- Changing Harness workflow.

## Work Phases

1. Discovery.
2. Design.
3. Validation planning.
4. Implementation.
5. Verification.
6. Harness update.

## Stop Conditions

Pause for human confirmation if:

- Validation requirements need to be weakened.
- The source-of-truth hierarchy changes.
- The workflow blocks bootstrap setup.
- The implementation requires remote secrets or external service access.

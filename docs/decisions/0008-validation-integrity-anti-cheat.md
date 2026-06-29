# 0008 Validation Integrity Anti-Cheat Controls

Date: 2026-06-29

## Status

Accepted

## Context

The Harness already records intake, stories, proof flags, verification commands,
traces, and interventions. That mitigates false "done" claims, but it does not
fully prevent agents from changing the rules that judge their own work.

High-risk failure modes include:

- Marking proof flags without independent verification.
- Weakening tests or fixtures so broken behavior passes.
- Editing CI workflows or Harness policy to remove checks.
- Treating trace text as final evidence.
- Narrowing scope after failure without a visible decision.

## Decision

Add a validation integrity layer with protected surfaces, CODEOWNERS, PR
checklists, CI hooks, and a local mechanical script.

Normal and high-risk work must treat validation, test, CI, trace, and Harness
policy changes as review-sensitive. Weakening validation requires a durable
decision record. CI or another independent verifier should produce final proof
when a shared branch or remote exists.

## Alternatives Considered

1. Rely on story verification and trace scoring only. Rejected because those
   records can still be self-reported or weakened by the same actor doing the
   task.
2. Wait for a full app stack and CI before documenting the policy. Rejected
   because the Harness itself is already defining how future work will be
   judged.
3. Make every validation change impossible for agents. Rejected because agents
   need to improve tests and Harness policy, but those changes must be visible
   and reviewable.

## Consequences

Positive:

- Protected policy and proof surfaces become explicit.
- Test weakening, CI workflow changes, and proof changes require stronger
  evidence.
- Future CI can run the same local validation integrity script.
- The PR template forces validation integrity questions into review.

Tradeoffs:

- Bootstrap mode is needed before the first baseline commit.
- CODEOWNERS must be configured with real owners before branch protection is
  fully effective.
- Some anti-cheat controls remain advisory until a remote and CI are active.

## Follow-Up

- Replace `@repo-owner` in `.github/CODEOWNERS` with real owners.
- Add CI required status checks after a remote exists.
- Add stack-specific coverage, mutation, security, and E2E providers when the
  application stack is selected.

# US-083 Post-Review Correctness Closure

## Current Behavior

The post-US-082 review records four open findings in
`docs/reviews/feature-self-improving-harness-lifecycle-to-main-review.md`:
mixed legacy/new resolver links lose precise ordering, migration 012 does not
normalize structured rejection reasons, rebuild validation can select a stale
binary, and exact proof snapshots reject legitimate later verification.

## Target Behavior

F-014 through F-017 are closed without weakening resolver proof, replay
identity, or rebuild validation. Upgraded and rebuilt databases expose the same
structured state, and validation proves which executable it tested.

## Affected Users

- Harness CLI operators completing resolver stories after schema upgrades.
- Maintainers recording later story verification evidence.
- Reviewers relying on rebuild validation as branch proof.

## Non-Goals

- Replacing semantic changesets or the E09 lifecycle.
- Inventing precise order for fully legacy events.
- Removing verification timestamps from durable story state.

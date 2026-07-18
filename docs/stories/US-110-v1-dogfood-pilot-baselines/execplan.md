# US-110 V1 Dogfood And Pilot Baselines Exec Plan

Status: **Repository-owned implementation complete / external enrollment and baseline execution blocked**

## Goal

Produce a stable, reviewable repository-owned Phase 5 candidate that dogfoods
V1 without path churn, freezes deterministic pilot evidence contracts, and
fails closed until two external owners supply real baseline evidence.

## Scope

In scope:

- Map Repository Harness's accepted Phase 4 paths in place with byte and Git
  provenance.
- Freeze concrete P0-P7 card revision 1.
- Define closed schemas for enrollment, environment, eligibility,
  inapplicability, owner signature/digest binding, intervention totals, and
  baseline results.
- Add positive and negative executable verification and minimal premerge
  wiring.
- Update US-105, the refactor plan, and test matrix from stale Phase 4 text to
  Phase 5 candidate tracking.

Out of scope:

- Any external repository access or mutation without owner authorization.
- Any invented pilot or evaluator evidence.
- Phase 5 acceptance, Phase 6 work, candidate comparison, Phase 7 release
  proof, or Phase 8 behavior.
- Phase 1-4 source changes, production keys, publishing, tags, remote branches,
  or changes to the six-command/four-command boundaries.
- `harness.db`, ignored databases, and `.harness/changesets`.

## Risk Classification

Risk flags:

- Public contracts: the evidence formats determine what may count as a fixed
  pilot baseline.
- Existing behavior: Phase 1-4 gates and ordinary-work optionality must remain
  unchanged.
- Weak proof: no authorized external baseline evidence exists yet.
- Multi-domain: repository mapping, evaluation integrity, external ownership,
  and premerge validation meet at this gate.

Hard gates:

- External-system/authorization boundary: pilot owners control repository
  access, revision, signature, and evidence custody.
- Validation integrity: missing baselines cannot be reconstructed after Phase
  6 candidate results exist.

No new durable decision is needed because this packet implements the exact
accepted Phase 5 protocol in `docs/REFACTOR_PLAN.md` and US-105 without
changing its architecture, authorization, or acceptance rules.

## Work Phases

1. Bootstrap against the explicitly supplied read-only planning database and
   confirm intake #7/active US-105 context without touching root `harness.db`.
2. Read Phase 5 authority, accepted Phase 1-4 boundaries, high-risk templates,
   and existing verifier/premerge conventions.
3. Pin the accepted Phase 4 source revision and map only current useful files;
   reject every rename or mapped deletion.
4. Freeze P0-P7 and schemas, then implement semantic cross-record checks for
   revisions, card signatures/digests, environments, eligibility, totals, and
   baseline identity.
5. Record and execute the repository-native ordinary documentation task with
   zero V1 core commands.
6. Exercise the test-only positive packet and negative mutations. Confirm that
   the empty live evidence index returns blocker exit 2.
7. Run affected Phase 1-4 verifiers, formatting/lint/tests, diff checks, and
   commit the stable candidate in this worktree only.

## Stop Conditions

Stop and request owner input if:

- A pilot repository, revision, owner approval, signer, evaluator, environment,
  or result would have to be guessed.
- An external repository must be opened or changed without explicit owner
  authorization.
- Phase 5 acceptance or Phase 6 execution is requested before two complete
  baselines exist.
- A useful Repository Harness path would need to move or duplicate.
- Verification would need to weaken a Phase 1-4 contract, the six-command
  core, four-command bridge, production gate, or archive custody rule.
- A dependency or lockfile becomes necessary; explain the need before adding
  it.

Current stop result: repository-owned work can complete, but live enrollment
and baseline work stops because no external pilot owner authorization exists.

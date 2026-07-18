# US-110 V1 Dogfood And Pilot Baselines

Status: **Corrected repository-owned Phase 5 candidate / external pilot evidence blocked / Phase 5 not accepted**

## Current Behavior

Phases 1-4 are accepted at source tree `0f81d3f0f4c8`, represented by commit
`04f953d0f4c8aa42689c1565178376143916c8b5` in this isolated checkout. V1 has
the six-command core, four-command archive bridge, authenticated contracts,
safe mutation/recovery, and deterministic Phase 1-4 proof. It does not yet have
two authorized external pilots, signed owner card sets, environment locks, or
baseline results.

Repository Harness already has useful paths such as `AGENTS.md`, `README.md`,
`docs/ARCHITECTURE.md`, `docs/decisions/`, `docs/stories/`, and
`docs/TEST_MATRIX.md`. Moving them to default V1 candidate names would break
links and obscure history without improving agent discovery. Ordinary
repository work also continues to use target-owned documents, scripts, Rust
checks, and Git; a V1 core command is not a prerequisite.

## Target Behavior

The repository-owned Phase 5 candidate has three effects:

1. `tests/evals/v1-phase5/dogfood/repository-map.json` maps the accepted Phase
   4 bytes to their current paths as target-owned, brownfield-mapped,
   `never-auto-patch` roles. Because the map adopts those paths, this commit
   needs no rename, duplicate document, or cosmetic directory.
2. `tests/evals/v1-phase5/dogfood/ordinary-task.json` records and executes a
   representative documentation task using `rg` and Git only. Because the
   verifier rejects all six V1 core invocations, the ordinary path proves zero
   core commands rather than relying on prose.
3. Fixed P0-P7 cards, JSON Schemas, and the corrected verifier define the exact
   records external owners must supply. Trust comes from an independently
   populated owner registry outside each packet. A verified SSH Ed25519
   statement binds canonical repository, resolved bundled commit, scope,
   catalog, complete packet-manifest digest, custody/publication identity, and
   baseline-before-disclosure timeline. Because no owner has authorized a
   pilot, the registry/index stay empty and explicit live proof exits 2.

Exact Phase 5 acceptance remains the authority in `docs/REFACTOR_PLAN.md`: no
required path move; no ordinary-task Harness core call; and at least two
unrelated, owner-authorized pilots, each with an immutable starting revision,
complete P0-P7 eligibility, independently authenticated complete packet,
environment lock, resolved repository revision, and a baseline result or
written inapplicability for every card, including complete intervention/time
totals. This candidate satisfies the repository-owned first two conditions and
defines/verifies the evidence format; it does not satisfy external-pilot
conditions.

## Affected Users

- Repository Harness maintainers can review an exact in-place role map and run
  one deterministic Phase 5 verifier.
- Pilot owners retain authorization, repository access, revision selection,
  signature, and evidence-custody authority.
- Evaluators receive fixed fields and rejection rules, so hidden help and
  omitted time cannot be normalized away.
- Agents doing ordinary work continue to use target-native paths and checks
  without a mandatory Harness command.
- Release maintainers receive candidate-only evidence; they receive no Phase 5
  acceptance, Phase 6 start, release, tag, or promotion authority.

## Affected Product Docs

- `docs/REFACTOR_PLAN.md`
- `docs/TEST_MATRIX.md`
- `docs/stories/US-105-harness-v1-implementation/**`
- `docs/stories/US-110-v1-dogfood-pilot-baselines/**`
- `tests/evals/v1-phase5/**`

## Non-Goals

- Accessing or changing an external pilot repository before its owner gives
  separate explicit authorization.
- Inventing pilot owners, approvals, repository revisions, signatures,
  environments, runs, interventions, inapplicability findings, or results.
- Marking Phase 5 accepted, starting Phase 6, promoting a release, creating
  production keys, publishing, tagging, pushing, or opening a pull request.
- Moving useful paths, creating duplicate knowledge documents, or making a V1
  core command mandatory during ordinary work.
- Changing Phase 1-4 implementation code, the six-command core, four-command
  bridge, production gates, compatibility dates, or archive custody policy.

Pilot authorization is a hard boundary: an empty trust registry and evidence
index are correct until two owners act. The verifier generates an ephemeral
SSH Ed25519 key and local Git bundle only inside temporary adversarial tests;
neither is trusted live pilot evidence.

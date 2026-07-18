# V1 Phase 5 Evaluation Contracts

This directory is the repository-owned Phase 5 evaluation surface. It is not a
pilot result and it is not installed by the V1 core.

`cards/` freezes P0-P7 at card revision 1. `schemas/` defines closed
machine-readable records for enrollment, environment, eligibility,
owner-signature/digest binding, interventions, and baseline results.
`dogfood/` maps Repository Harness's accepted Phase 4 tree in place and records
one ordinary documentation task whose check uses zero V1 core commands.
`evidence/index.json` deliberately contains no pilots because no external
repository owner has authorized access or supplied evidence.

For an authorized pilot, create one custody directory named by `pilot_id` and
include these schema-valid files: `enrollment.json`, `environment.json`,
`eligibility.json`, `card-set.signature.json`, `interventions.json`, and
`baseline-result.json`. The owner signature binds the exact SHA-256 of
`cards/catalog.json`; the enrollment and result repeat that digest. Each
environment and result digest is computed over UTF-8 canonical JSON with its
own digest field omitted. A signature is accepted structurally only when its
subject digest matches; the named owner/evaluator remains responsible for
verifying the declared external signature algorithm and retaining that proof
at `authority_ref`.

Cause and effect is fail-closed:

1. An owner authorizes an exact repository and scope.
2. Enrollment pins a 40-character Git commit, so later branch movement cannot
   rewrite the baseline starting point.
3. The environment lock fixes model, reasoning, tools, permissions, evaluator,
   fixtures, and acceptance commands, so a changed condition requires rerun.
4. Eligibility contains all P0-P7; an inapplicable card needs a non-empty
   evaluator finding, so a difficult card cannot disappear silently.
5. Intervention totals are recomputed from events, so reported human attention
   cannot omit setup, relay, correction, or review time.
6. A baseline result accepts only `run_kind=baseline` and the same revision,
   card-set digest, and environment digest. Candidate fields therefore cannot
   masquerade as baseline evidence.

Run the repository-owned positive and negative contracts plus dogfood proof:

```bash
scripts/verify-v1-phase5-evidence.sh
```

After two owners supply real packets, require the live evidence gate:

```bash
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines
```

The second command currently exits 2 and lists the authorization/evidence
blockers. Do not change that result until two unrelated authorized pilots have
real baseline packets.

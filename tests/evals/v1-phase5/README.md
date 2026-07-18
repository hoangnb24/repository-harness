# V1 Phase 5 Evaluation Contracts

This directory is the repository-owned Phase 5 evaluation framework. It is not
pilot evidence and is not installed by the V1 core.

`cards/` freezes P0-P7 at revision 1. `schemas/` defines closed records for
trusted owners, enrollment, environment, eligibility, interventions, baseline
results, complete packet manifests, and authenticated publication.
`dogfood/` pins the accepted Phase 4 source bytes and executes only three exact
argv arrays: two `rg --no-config` searches and `git --no-optional-locks diff
--no-ext-diff --check`. `evidence/` contains an empty trusted-owner registry and no pilots
because no external owner authorization or key has been supplied.

## Live Packet Contract

An authorized pilot directory is named exactly by `pilot_id` beneath
`tests/evals/v1-phase5/evidence/`. It contains:

- `enrollment.json`
- `environment.json`
- `eligibility.json`
- `interventions.json`
- `baseline-result.json`
- `repository.bundle`
- every referenced fixture, transcript, and evidence artifact
- `packet-manifest.json`
- `authentication.json`

The pilot directory may contain no unlisted file or symlink. All paths are
relative canonical POSIX paths; absolute paths, `..`, backslashes, custody-root
escapes, and mismatched directory names fail.

Trust is independent of the packet. A repository maintainer records an
owner-approved `ssh-ed25519` public key, stable owner identity, canonical HTTPS
`.git` repository identity, exact authorization scope, trust source, and trust
time in `evidence/trusted-owners.json`. A packet cannot declare its own trusted
key or widen that scope.

`packet-manifest.json` lists exact SHA-256 digests for enrollment, environment,
eligibility, interventions, baseline result, repository bundle, and every
referenced fixture/transcript/evidence file. `authentication.json` contains a
closed SSH signature envelope. `ssh-keygen -Y verify` verifies the signature
offline under namespace `repository-harness-phase5` against the independently
trusted owner key.

The signed canonical statement binds:

- pilot and owner identities;
- canonical repository identity and full starting commit;
- authorization scope and fixed card-catalog digest;
- complete packet-manifest digest;
- immutable custody and baseline-publication identities;
- the manifest-backed pre-candidate baseline-subject identity and digest;
- baseline start/completion, authenticated publication, and
  candidate-disclosure-not-before timestamps.

The repository bundle is digest-bound by the manifest. The verifier imports it
into an isolated bare repository and requires the named 40-character commit to
resolve as a commit object. An arbitrary hex string or repository alias cannot
substitute for that evidence.

All times use strict RFC 3339 UTC seconds. The enforced order is trust <=
authorization <= environment lock/eligibility <= baseline start <= baseline
completion <= authenticated publication <= candidate disclosure. Intervention
events must occur within the baseline interval.

Environment tools have unique names and versions; enabled tools are a subset.
Fixtures and all result evidence must be authenticated manifest members. Each
eligible P0-P7 result binds its locked acceptance argv and supplies one
manifest artifact for every card-specific evidence requirement. Inapplicable
cards bind authenticated evaluator findings and artifacts. The baseline binds
the exact intervention-log digest and names a concrete
`pre-candidate-baseline` evaluation subject whose artifact and digest resolve
inside the authenticated manifest.

## Commands

Run framework, cryptographic positive, adversarial negative, and dogfood proof:

```bash
scripts/verify-v1-phase5-evidence.sh
```

When the index remains `candidate-awaiting-pilot-authorization`, explicit live
proof exits 2 and prints blockers:

```bash
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines
```

If the index is changed to `complete`, the default/premerge invocation
automatically loads and verifies every packet and requires at least two pilots
with pairwise-distinct canonical repositories, owner IDs, and owner identities.
A shallow complete index can never pass.

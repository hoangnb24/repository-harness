# V1 Phase 5 Evaluation Contracts

This directory is the repository-owned Phase 5 evaluation framework. It is not
pilot evidence and is not installed by the V1 core.

`cards/` freezes P0-P7 at revision 1. `schemas/` defines closed records for
trusted owners, enrollment, environment, eligibility, interventions, baseline
results, complete packet manifests, and authenticated publication.
`dogfood/` pins the accepted Phase 4 source bytes and executes only three exact
argv arrays: two `rg --no-config` searches and `git --no-optional-locks diff
--no-ext-diff --check`. `evidence/trusted-owners.json` is a required empty
placeholder, not a trust anchor, and `evidence/` contains no pilots because no
external owner authorization or key has been supplied.

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

Live trust is an invocation input outside the candidate repository. The caller
must supply an absolute, non-symlink registry path and its independently pinned
SHA-256 with `--trusted-owner-registry` and
`--trusted-owner-registry-sha256`. The registry records each `ssh-ed25519`
public key, stable owner identity, canonical HTTPS `.git` repository identity,
exact authorization scope, trust source, and trust time. A tracked entry can
never authorize a pilot: the verifier requires the repository placeholder to
remain empty and rejects an external registry located inside this repository.

The verifier proves that packets authenticate under the exact caller-supplied
registry bytes; it does not prove who authorized those bytes. The invoking
reviewer remains responsible for obtaining the registry and digest through an
independent owner-authorization channel.

`packet-manifest.json` lists exact SHA-256 digests for enrollment, environment,
eligibility, interventions, baseline result, repository bundle, and every
referenced fixture/transcript/evidence file. `authentication.json` contains a
closed SSH signature envelope. `ssh-keygen -Y verify` verifies the signature
offline under namespace `repository-harness-phase5` against the caller-pinned
external owner key.

The signed canonical statement binds:

- pilot and owner identities;
- canonical repository identity and full starting commit;
- authenticated repository-bundle SHA-256 identity;
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
A tool name and every acceptance `argv[0]` use the same case-sensitive bare
executable token grammar `[A-Za-z0-9][A-Za-z0-9._+-]*`. Every eligible card's
locked command must resolve by exact name to one versioned tool and that tool
must be enabled; paths, aliases, and undeclared executables cannot satisfy this
rule.
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
automatically enters the live gate and fails closed unless the two external
trust arguments are supplied. With those inputs it verifies every packet and
requires pairwise-distinct canonical repositories, owner IDs, owner identities,
SSH Ed25519 key fingerprints, and authenticated repository-bundle SHA-256
identities. A shallow complete index, one reused key, or one reused bundle can
never pass.

Example live invocation after authorization exists:

```bash
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines \
  --trusted-owner-registry /absolute/external/trusted-owners.json \
  --trusted-owner-registry-sha256 <lowercase-sha256>
```

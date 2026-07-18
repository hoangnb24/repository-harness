# US-110 V1 Dogfood And Pilot Baselines Design

Status: **Corrected repository-owned Phase 5 candidate / live gate blocked**

## Domain Model

`DogfoodMap` binds the accepted Phase 4 revision to existing useful paths by
Git blob and SHA-256. Every mapped path is already a Phase 1
`target-owned-destination`, so dogfood neither moves a path nor reclassifies V0
operational content as V1 payload.

`PilotCard` fixes one P0-P7 prompt, applicability rule, acceptance tests,
mandatory failures, and evidence requirements. `CardCatalog` contains exactly
P0-P7 and exact file digests.

`TrustedOwner` is caller-supplied material outside both a pilot packet and the
candidate repository: owner ID, stable owner identity, canonical HTTPS `.git`
repository, exact authorization scope, `ssh-ed25519` public key, trust source,
and strict RFC 3339 UTC trust time. Its exact bytes are pinned by a required
CLI SHA-256. The tracked registry is an enforced-empty placeholder and cannot
authorize a packet. The verifier authenticates against caller-supplied bytes;
the caller, not the machine, establishes their independent authorization.

`PilotEnrollment` repeats the trusted owner ID, canonical repository, exact
scope, authorization time, card catalog digest, and full Git starting commit.
It names an authenticated `repository.bundle`; the verifier imports that bundle
into an isolated bare repository and requires the commit to resolve.

`EnvironmentLock` fixes model, reasoning, OS/architecture, unique versioned
tools, enabled-tool subset, permissions, evaluator, authenticated fixtures, and
one exact acceptance argv per P0-P7. Tool names and each eligible card's
`argv[0]` are exact case-sensitive bare executable tokens. Each applicable
command executable must match one versioned tool and that tool must be enabled.
Its canonical digest omits only its digest field.

`Eligibility` contains exactly P0-P7. An eligible card has no contradictory
finding. An inapplicable card requires a non-empty evaluator finding and at
least one manifest-authenticated finding artifact.

`InterventionLog` records card, actor, strict UTC time, fixed taxonomy, reason,
positive whole minutes, and outcome effect. The verifier recomputes global,
per-card, and per-taxonomy totals and requires every event to fall inside the
baseline interval.

`BaselineResult` names a concrete `pre-candidate-baseline` subject identity and
digest, strict start/completion times, revision, catalog and environment
digests, exact P0-P7 outcomes, the locked acceptance command for each eligible
card, all card-specific evidence requirements, and the exact intervention-log
path/digest. Thus candidate absence is proven by a named baseline subject plus
an authenticated publication-before-disclosure timeline, not by omitting a
`candidate_identity` field.

`PacketManifest` lists exact digests for enrollment, environment, eligibility,
interventions, baseline, repository bundle, and every referenced fixture,
transcript, or evidence artifact. The directory may contain only those files,
the manifest, and authentication envelope. Absolute/traversal paths, unlisted
files, symlinks, or custody escapes fail.

`PacketAuthentication` uses exactly algorithm `ssh-ed25519` and namespace
`repository-harness-phase5`. `ssh-keygen -Y verify` checks the detached SSH
signature offline against the caller-pinned external trusted-owner key. The
signed canonical statement binds pilot/owner, repository, resolved commit,
repository-bundle SHA-256, scope, catalog digest, complete manifest digest,
immutable custody/publication IDs, manifest-backed baseline-subject
identity/digest, baseline times, publication time, and
candidate-disclosure-not-before.

## Application Flow

Repository-owned dogfood flow:

1. Resolve the accepted Phase 4 commit/blob/digest for each mapped path.
2. Reject any rename or mapped deletion.
3. Require the ordinary transcript to equal three closed argv arrays: two
   `rg --no-config` searches and
   `git --no-optional-locks diff --no-ext-diff --check`.
4. Remove Git config/alias/exec-path and ripgrep-config environment inputs.
5. Convert missing executables into deterministic verification failures.

Authorized pilot flow:

1. Require the tracked trust placeholder to be empty. For a complete live gate,
   hash and load the explicit external trust registry and reject duplicate IDs
   or signing-key fingerprints.
2. Load the evidence index. A `complete` index automatically enters full live
   verification even under the default/premerge command.
3. Resolve each relative pilot directory beneath the evidence root and reject
   symlinks, traversal, or directory-name mismatch.
4. Verify every packet-manifest member/digest and exact directory inventory.
5. Validate enrollment, environment, eligibility, interventions, and baseline.
6. Verify the SSH Ed25519 signature over the canonical publication statement.
7. Match statement, trusted owner, enrollment, manifest, and baseline
   repository/owner/scope/revision/catalog/environment/intervention identities.
8. Import the authenticated bundle and resolve the exact starting commit.
9. Enforce trust/authorization/run/publication/disclosure chronology.
10. Require pairwise-distinct canonical repositories, owners, signing-key
    fingerprints, and authenticated repository-bundle digests.

Current candidate flow stops before step 3 because the index is awaiting owner
authorization and has no pilots.

## Interface Contract

```text
scripts/verify-v1-phase5-evidence.sh
scripts/verify-v1-phase5-evidence.sh --dogfood-only
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines \
  --trusted-owner-registry /absolute/external/trusted-owners.json \
  --trusted-owner-registry-sha256 <sha256>
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY=/absolute/external/trusted-owners.json \
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256=<sha256> \
  scripts/validate-premerge.sh
```

Default success returns 0 only for a valid candidate framework or a fully
verified complete live index. Malformed contracts/evidence return 1. Explicit
live proof returns 2 while the index is awaiting authorization. A complete
index without both external trust arguments fails closed. Dogfood-only
validates the in-place map and exact ordinary argv.

Premerge itself accepts no arguments. It recognizes only the paired
`HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY` and
`HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256` variables, validates the
absolute-path/lowercase-digest shape, rejects partial or unknown prefixed
inputs, unsets them, and forwards the corresponding four arguments with a Bash
array. Therefore an operator can supply live trust without creating a route to
`--dogfood-only` or another Phase 5 bypass.

The wrapper preflights `git`, `python3`, `rg`, and `ssh-keygen`. Schemas live
under `tests/evals/v1-phase5/schemas/`; the full custody layout is documented in
`tests/evals/v1-phase5/README.md`.

## Data Model

Records are closed UTF-8 JSON. Self-digests use sorted-key compact UTF-8 JSON
with only the self-digest field omitted. Card, manifest-member, bundle, and
packet-manifest identities bind exact file bytes with lowercase SHA-256.

Pilot paths are relative canonical POSIX paths beneath
`tests/evals/v1-phase5/evidence/<pilot_id>/`. No SQLite database, migration,
changeset, telemetry row, task state, V1 manifest, production key, or external
repository write is created.

## UI / Platform Impact

There is no product UI, core CLI, bridge, installer, or release change. The
verifier requires Python 3, Git, ripgrep, and OpenSSH `ssh-keygen`. Five-platform
product equivalence remains Phase 7.

## Observability

The verifier prints numbered proof groups. The positive packet uses an
ephemeral generated test key and local synthetic Git bundle; neither is written
to live evidence. Adversarial tests reproduce forged signatures, fake commits
and repositories, timestamp reversal, unsigned rewrites, shallow complete
indexes, same-owner/repository/key/bundle pilots, tracked self-authorization,
undeclared acceptance executables, custody escapes, environment/evidence
inconsistency, Git alias bypass, missing ripgrep, and subprocess OSError.
`tests/evals/test-phase5-premerge-trust-forwarding.sh` copies premerge into an
isolated temporary harness and proves exact paired argv, both partial failures,
CLI/environment bypass rejection, reserved-variable removal, and zero-argument
current-candidate behavior without pilot evidence.

The live gate prints blockers and exits 2 without logging owner secrets or
inventing credentials. A future `complete` index cannot bypass packet loading
because default/premerge automatically runs the live gate.

## Alternatives Considered

1. Accept a non-empty structural signature field. Rejected because `x` is not
   authentication.
2. Let packets provide their own owner key. Rejected because self-declared trust
   does not prove owner authorization.
3. Resolve a 40-hex string without repository evidence. Rejected because an
   arbitrary value could pass.
4. Sign only `catalog.json`. Rejected because enrollment, interventions, and
   results could change unsigned.
5. Trust missing candidate fields. Rejected in favor of named baseline subject
   and authenticated pre-disclosure publication.
6. Execute generic `git` or `rg` strings. Rejected because aliases, exec-path,
   config, or preprocessors could invoke hidden commands.
7. Add live placeholders. Rejected because no external owner has authorized a
   repository, key, revision, or run.
8. Treat a tracked trust entry as owner authorization. Rejected because a
   submitter controls candidate bytes; live trust must be supplied and
   digest-pinned by the invoking authority outside the repository.

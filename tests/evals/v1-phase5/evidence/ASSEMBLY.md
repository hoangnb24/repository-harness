# Phase 5 Live Evidence Packet Assembly

The two live packets were assembled on 2026-07-18 from committed pilot
evidence. A later independent review found that selected historical evidence
artifacts still named source-run environment digests computed with a trailing
newline even though packet assembly correctly used the verifier-canonical
no-newline digests:

- benchmark legacy
  `b69c81a8ec42c39d80b0b9f814675646c4f1e39f688aa5a72bab01265e480dde`
  maps to canonical
  `b3a3067d79803aa6631ae7cd9f3424e13b102073bd9eb64123407a9ae43ef2dc`;
- e-inna legacy
  `1808dd68477e80c0fdb5bb04b4f1e99b280886432046022deb85772494af8256`
  maps to canonical
  `1a2c1145670897c3d85a0fb9509704f3b70174a38fd0a6ae69e38d0b9f3c1f15`.

This correction adds explicit post-run annotations to the five legacy
references and canonical bindings to all four exact P3/P6 requirement-mapped
artifacts. Those annotated artifacts intentionally no longer byte-match their
source Git blobs; their original values, prompts, transcripts, outcomes,
timestamps, interventions, and other source facts remain visible and
unchanged.

Packet provenance remains:

- `harness-benchmark-phase5-pilot` uses
  `docs/evidence/phase5-pilot-benchmark` at clean source commit
  `024a05a2a5e5a2993e79c50d395059cd754dfda1`. Its committed
  `repository.bundle` was retained after verifying that it resolves starting
  commit `090f6d1c33d9f006cc8e95491badc33a8053c89f`.
- `e-inna-brain-phase5-baseline` uses
  `docs/evidence/phase5-pilot-einna` at clean source commit
  `975c7a2110774eab553feda018042ec04b1fa0cb`. Its bundle was created with
  `git bundle` from the primary repository at exact tracked-clean HEAD
  `9be2b9b624f29c2c4f93bb576485fd8de2085af4`; no untracked source path was
  copied or modified.

The external trusted-owner registry remained outside this repository at the
operator-supplied path. Its verified SHA-256 is
`f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d`.
The tracked `trusted-owners.json` remains empty.

Verifier-readiness normalization changed representation, not recorded run
facts: repository-scoped enrollment identities and scopes were applied;
eligible-card findings were cleared; only benchmark P1 remains inapplicable;
eligible acceptance commands were serialized as canonical `{"argv":[...]}`
JSON; card evidence requirements were aligned exactly with the fixed catalog;
and environment, result, intervention-file, bundle-file, packet-artifact, and
manifest digests were recomputed. Recorded timestamps, interventions, and all
pass/fail/inapplicable outcomes were preserved.

Only the affected packet-manifest artifact digests were updated. Each
authentication statement was rebound to its corrected packet manifest and
authenticated with its externally held SSH Ed25519 pilot key. The evidence
index names both corrected packets and has no remaining blocker.

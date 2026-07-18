# Phase 5 Live Evidence Packet Assembly

The two live packets were assembled and authenticated on 2026-07-18 from
committed pilot evidence only:

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

Both authentication envelopes bind their complete canonical statements and
carry SSH Ed25519 signatures made with the two externally held pilot keys.
The complete evidence index names both packets and has no remaining blocker.

# US-110 V1 Dogfood And Pilot Baselines Validation

Status: **Corrected candidate proof defined / live pilot proof absent**

## Proof Strategy

The default verifier proves path-stable dogfood, closed schemas/cards, an
ephemeral actually signed positive packet, and adversarial rejection. Candidate
status may pass the framework with no pilots. If the index ever says
`complete`, the same default/premerge command automatically loads every packet,
verifies owner trust/signature/repository/custody/timeline/evidence, and requires
two independent pilots. Explicit live mode exits 2 now.

Exact Phase 5 acceptance still requires all of these together:

1. No required Repository Harness path move or duplicate knowledge path.
2. The fixed ordinary task executes only its exact allowlisted argv with zero
   V1 core commands and no Harness-only durable plan.
3. At least two pairwise-distinct canonical repositories, owner identities,
   SSH Ed25519 key fingerprints, and authenticated repository-bundle digests
   are evaluated against a caller-pinned registry outside the repository. The
   machine validates that input but does not claim to prove its authorization
   provenance.
4. Each digest-bound repository bundle resolves the named immutable commit.
5. Each offline SSH Ed25519 signature authenticates repository/commit/scope,
   card catalog, complete packet manifest, custody/publication identity,
   manifest-backed baseline-subject identity/digest, and the
   baseline-before-candidate-disclosure timeline.
6. Each manifest covers enrollment, environment, eligibility, interventions,
   baseline, repository bundle, fixtures, transcripts, and every result/finding
   artifact without symlink or custody escape.
7. Every environment is internally consistent; each applicable acceptance
   `argv[0]` exactly names one enabled versioned bare-token tool; every P0-P7
   result binds its locked acceptance argv and card-specific evidence;
   inapplicability findings and intervention totals are authenticated.
8. Corrected Phase 5 and affected Phase 1-4 regressions pass, followed by
   independent acceptance.

Conditions 1-2 and the verifier/framework portion of 3-8 are repository-owned.
No external trusted owner, repository bundle, revision, signature, run, or
result exists. Phase 5 is not accepted and Phase 6 remains closed.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Closed schema fields/enums; strict UTC parsing/order; canonical HTTPS repository; safe relative custody paths; complete P0-P7; unique/subset tools; totals; exact ordinary argv. |
| Integration | SSH Ed25519 sign/verify; complete manifest/digest inventory; isolated Git bundle import and commit resolution; environment/eligibility/intervention/baseline cross-binding. |
| E2E | Default corrected verifier passes candidate framework; dogfood-only passes; explicit live gate exits 2; shallow `complete` index fails. |
| Platform | Current macOS shell/Python/Git/ripgrep/OpenSSH execution. Five-platform product proof remains Phase 7. |
| Performance | Bounded local files and temporary Git/SSH fixtures; no performance release claim. |
| Logs/Audit | Numbered proof groups and deterministic failures; no owner secrets, live telemetry, or fabricated evidence. |

## Fixtures

- Fixed repository-owned P0-P7 catalog.
- Accepted Phase 4 source commit
  `04f953d0f4c8aa42689c1565178376143916c8b5` and target-owned path blob/SHA
  provenance.
- One temporary synthetic Git repository/bundle and ephemeral SSH Ed25519 key,
  supplied through an out-of-repository test registry with its exact digest and
  deleted with its temporary directory. This proves input binding, not external
  authorization provenance.
- Thirty-two adversarial cases covering the confirmed forged packet,
  one-character/unknown signatures, malformed and
  post-disclosure times, fake repository/commit, unsigned intervention rewrite,
  same-repository/same-owner pilots, absolute/traversal/symlink/mismatched
  custody, shallow complete index, one-key/one-bundle aliased pilots, tracked
  self-authorization, undeclared acceptance executables, inconsistent
  tools/fake evidence, Git alias core-call bypass, subprocess OSError, and
  missing ripgrep.
- Empty tracked trust placeholder and pilot index with real blockers only.

## Commands

```bash
scripts/verify-v1-phase5-evidence.sh
scripts/verify-v1-phase5-evidence.sh --dogfood-only
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines  # expected exit 2
tests/evals/test-phase5-premerge-trust-forwarding.sh
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY=/absolute/external/trusted-owners.json \
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256=<lowercase-sha256> \
  scripts/validate-premerge.sh  # future authorized full-premerge form
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
tests/docs/test-doc-contracts.sh
python3 -m py_compile scripts/verify_v1_phase5_evidence.py
bash -n scripts/verify-v1-phase5-evidence.sh scripts/validate-premerge.sh
cargo fmt --all -- --check
git diff --check
```

## Acceptance Evidence

The corrected repository-owned candidate is enforced by
`scripts/verify-v1-phase5-evidence.sh` and is wired into default premerge. Its
positive signature/repository packet is temporary test evidence, not a pilot.

Current live result remains blocked: `evidence/trusted-owners.json` is an
enforced-empty placeholder and `evidence/index.json` contains no pilot. No
external trust registry/hash has been supplied. Explicit live mode must exit 2.
This is correct negative evidence, not Phase 5 acceptance.

Correction-candidate results on 2026-07-18:

- Corrected Phase 5 verifier: **5/5 proof groups passed**, including one
  ephemeral packet whose SSH Ed25519 signature is actually verified and whose
  named commit resolves from its authenticated Git bundle.
- Adversarial suite: **32/32 rejected**, covering the confirmed oracle,
  external/tracked trust boundary, repository/key/bundle identity, manifest,
  timeline, independence, custody, acceptance-tool/environment/evidence,
  subprocess, Git-alias, missing-ripgrep, and legacy negative cases.
- Dogfood-only: **1/1 passed** with exact closed argv and no path move.
- Explicit live gate: **expected exit 2** with no owner trust or pilot packet.
- Premerge trust forwarding: **6/6 cases passed under macOS `/bin/bash`
  3.2.57** for literal zero-argument no-input invocation, exact pair
  forwarding (including a path containing spaces), both partial rejections,
  CLI bypass rejection, and unknown-environment rejection. Ordered per-case
  markers prove every case completed.
- Phase 1-4 regressions: **10/10, 11/11, 11/11, and 10/10 proof groups
  passed**.
- Rust workspace within premerge: **203 tests passed, 0 failed**.
- Documentation contract, JSON parsing, Python compilation, shell syntax,
  formatting, `git diff --check`, and full premerge repository contract passed.

Only two complete independently owned live packets and independent review can
accept Phase 5; Phase 6 remains closed.

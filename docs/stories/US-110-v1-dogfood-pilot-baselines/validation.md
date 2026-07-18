# US-110 V1 Dogfood And Pilot Baselines Validation

Status: **Authenticated live baseline gate passed on exact `b2dd775` / Phase 5 accepted / Phases 6-8 not started**

## Proof Strategy

The default verifier proves path-stable dogfood, closed schemas/cards, an
ephemeral actually signed positive packet, and adversarial rejection. Candidate
framework status is separable from live packet acceptance. When the index says
`complete`, the same default/premerge command automatically loads every packet,
verifies owner trust/signature/repository/custody/timeline/evidence, and requires
two packets for distinct canonical repositories. A complete index with the
caller-pinned registry/hash passes the live gate; without those trust arguments
the verifier fails closed.

Exact Phase 5 acceptance still requires all of these together:

1. No required Repository Harness path move or duplicate knowledge path.
2. The fixed ordinary task executes only its exact allowlisted argv with zero
   V1 core commands and no Harness-only durable plan.
3. At least two pairwise-distinct canonical repositories,
   repository-scoped owner IDs, and authenticated repository-bundle digests are
   evaluated against a caller-pinned registry outside the repository. The same
   stable `owner_identity` may authorize both repositories. An SSH Ed25519 key
   fingerprint may repeat only for that same stable identity across the
   distinct repository scopes; separate per-repository evaluation keys remain
   recommended. The machine validates that input but does not claim to prove
   its authorization provenance.
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
The live gate now verifies two complete authenticated packets; Phase 5 accepts
their honest pre-candidate baseline custody. Phase 6 remains closed.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Closed schema fields/enums; strict UTC parsing/order; canonical HTTPS repository with raw path/hostname alias rejection; safe relative custody paths; complete P0-P7; unique/subset tools; totals; exact ordinary argv. |
| Integration | SSH Ed25519 sign/verify; complete manifest/digest inventory; isolated Git bundle import and commit resolution; environment/eligibility/intervention/baseline cross-binding. |
| E2E | Bare verifier fails closed without external trust; `--dogfood-only` is partial; the full caller-pinned live invocation passes the complete index; shallow `complete` index fails. |
| Platform | Current macOS shell/Python/Git/ripgrep/OpenSSH execution. Five-platform product proof remains Phase 7. |
| Performance | Bounded local files and temporary Git/SSH fixtures; no performance release claim. |
| Logs/Audit | Numbered proof groups and deterministic failures; no owner secrets, live telemetry, or fabricated evidence. |

## Fixtures

- Fixed repository-owned P0-P7 catalog.
- Accepted Phase 4 source commit
  `04f953d0f4c8aa42689c1565178376143916c8b5` and target-owned path blob/SHA
  provenance.
- Two temporary synthetic Git repositories/bundles and one ephemeral SSH
  Ed25519 key, supplied through two repository-scoped authorization records for
  one stable owner in an out-of-repository test registry with its exact digest
  and deleted with its temporary directory. This proves the allowed shared-owner
  topology and input binding, not external authorization provenance.
- Forty-two adversarial cases covering the confirmed forged packet, including
  both environment-digest attacks,
  one-character/unknown signatures, malformed and
  post-disclosure times, fake repository/commit, unsigned intervention rewrite,
  same-repository/same-owner-ID pilots, cross-identity key reuse, duplicate
  trust-registry repository scope, raw dot-segment and trailing-host-dot aliases
  in both registry and complete signed live-index validation, raw dot-dot and
  empty internal repository path segments,
  absolute/traversal/symlink/mismatched
  custody, shallow complete index, same-owner one-key/one-bundle aliased
  pilots, tracked self-authorization, undeclared acceptance executables,
  inconsistent tools/fake evidence, Git alias core-call bypass, subprocess
  OSError, and missing ripgrep.
- Complete evidence index naming the two pilots with `"blockers": []`; tracked
  trusted-owners remains empty and caller-pinned external trust is required.

## Commands

```bash
scripts/verify-v1-phase5-evidence.sh
scripts/verify-v1-phase5-evidence.sh --dogfood-only  # partial dogfood only
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines  # fails closed without trust
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines \
  --trusted-owner-registry /absolute/external/trusted-owners.json \
  --trusted-owner-registry-sha256 f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d
tests/evals/test-phase5-premerge-trust-forwarding.sh
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY=/absolute/external/trusted-owners.json \
HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256=<lowercase-sha256> \
  scripts/validate-premerge.sh  # current authorized full-premerge form
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

The authenticated live gate on exact `b2dd775` was invoked with the
caller-pinned registry outside the candidate repository at SHA-256
`f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d`.
Tracked `evidence/trusted-owners.json` remains empty. The command passed six
proof groups, rejected 42/42 adversarial cases, verified both SSH Ed25519
signatures and both bundle-resolved revisions, and accepted two packets with
distinct owner IDs, canonical repositories, bundles, and external keys under
one stable GitHub identity.

Packet IDs and source/revision identities are concrete: packet
`harness-benchmark-phase5-pilot` was assembled from source commit
`024a05a2a5e5a2993e79c50d395059cd754dfda1`, resolves starting revision
`090f6d1c33d9f006cc8e95491badc33a8053c89f`, and publishes as
`harness-benchmark-phase5-pilot-baseline-20260718t075654z`; packet
`e-inna-brain-phase5-baseline` was assembled from source commit
`975c7a2110774eab553feda018042ec04b1fa0cb`, resolves starting revision
`9be2b9b624f29c2c4f93bb576485fd8de2085af4`, and publishes as
`e-inna-brain-phase5-baseline-baseline-20260718t075654z`. The eight annotated artifacts
preserve source-run legacy digest truth while binding canonical packet digests.
Benchmark P1 is inapplicable and P6 failed; e-inna P0/P1/P3/P6 failed. These
are measurements of the pre-candidate baselines, not Phase 6 acceptance.

Historical correction-candidate results on 2026-07-18 (before the live packet
normalization and approval):

- Corrected Phase 5 verifier: **5/5 proof groups passed**, including two
  ephemeral repository-scoped packets for one stable owner and key; both SSH
  Ed25519 signatures are verified, both named commits resolve, and their
  repository and bundle identities differ.
- Adversarial suite: **40/40 rejected**, covering the confirmed oracle,
  external/tracked trust boundary, repository/key/bundle identity, manifest,
  raw repository aliases, timeline, independence, custody,
  acceptance-tool/environment/evidence,
  subprocess, Git-alias, missing-ripgrep, and legacy negative cases.
- Dogfood-only: **1/1 passed** with exact closed argv and no path move.
- Explicit live gate: **expected exit 2** (historical pre-packet state).
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
- Generated-artifact contract: both exact native/Windows
  `harness-v0-migrate` install paths are ignored, source and unrelated binary
  paths remain visible, and mandatory premerge requires its ending Git status
  to equal its starting Git status.

The same independent reviewer explicitly approved exact `b2dd775` with no
remaining findings; shared-owner alias hardening exact `c928986` was separately
approved by the earlier independent w1N rereviewer. Primary fast-forward
integration and trust-enabled full premerge passed on exact `b2dd775`;
acceptance documentation was integrated at `3a65768` and does not claim that
premerge result for itself.
Phase 6 remains not started.

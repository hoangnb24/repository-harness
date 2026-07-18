# US-110 V1 Dogfood And Pilot Baselines Validation

Status: **Repository-owned candidate proof defined / live pilot acceptance proof absent**

## Proof Strategy

The default verifier proves repository-owned contracts and dogfood behavior.
It must pass only when all current paths still exist in place, source bytes
match the accepted Phase 4 revision, P0-P7 are exact and digest-bound, schemas
validate, the ordinary-task checks execute with zero V1 core calls, and every
required negative mutation is rejected.

The live evidence gate is deliberately separate. It must exit 2 until two
unrelated owner-authorized pilots have complete packets. This cause/effect
prevents a green contract test from being reported as a pilot baseline.

Exact Phase 5 acceptance requires all of these conditions together:

1. No required Repository Harness path move or duplicate knowledge path.
2. A representative ordinary task completes with zero V1 core commands and no
   Harness-only durable plan.
3. At least two unrelated external pilot owners authorize evaluation and pin
   immutable starting commits and evidence custody.
4. Each pilot signs the exact P0-P7 catalog digest and locks model, reasoning,
   tools/versions, enabled tools, permissions, evaluator, OS/architecture,
   fixtures, and acceptance commands before baseline execution.
5. Every pilot records P0-P7 as eligible or supplies a written evaluator
   finding for inapplicability; no card is omitted.
6. Every eligible baseline result binds the same revision, catalog, and
   environment, and records complete intervention count/minutes by card and
   taxonomy.
7. The focused verifier and affected Phase 1-4 proof remain green for the exact
   candidate, followed by independent acceptance.

Conditions 1-2 and the format/verifier portion of 4-7 are repository-owned and
implemented here. Conditions 3-6 have no real external evidence. Therefore
Phase 5 is not accepted and Phase 6 remains not started.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Closed-schema types/required fields; exact P0-P7 set; canonical digests; complete intervention recomputation; core-command recognition. |
| Integration | Card catalog/file digests; dogfood Git blob/SHA provenance; in-place diff; ordinary-task command execution; cross-record pilot revision/catalog/environment consistency. |
| E2E | Default repository-owned candidate verifier passes; live pilot gate exits 2 with current authorization blockers. No browser E2E applies. |
| Platform | Shell/Python syntax and repository-native checks on the current supported development platform. Five-platform product evidence remains Phase 7. |
| Performance | Not a release criterion; the verifier reads a bounded card/schema/path set. |
| Logs/Audit | Numbered proof groups, deterministic failure messages, and explicit live blocker output; no pilot telemetry or raw secrets. |

## Fixtures

- Fixed repository-owned P0-P7 JSON files and digest catalog.
- Accepted Phase 4 source commit
  `04f953d0f4c8aa42689c1565178376143916c8b5` with pinned blobs/SHA-256 for
  mapped useful paths.
- One in-memory positive packet whose owner, repository, timestamps, algorithm,
  signature, tools, and evidence URLs are all labeled `TEST-ONLY` or
  `synthetic`.
- Negative in-memory mutations for changed revision, empty signature, wrong
  signed digest, test-only signature presented live, incomplete environment,
  omitted card, incomplete totals, candidate-as-baseline, path rename, and
  ordinary-task V1 core invocation.
- Empty live evidence index with actual authorization blockers. It contains no
  fabricated pilot identity or result.

## Commands

```bash
scripts/verify-v1-phase5-evidence.sh
scripts/verify-v1-phase5-evidence.sh --dogfood-only
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines  # expected exit 2 until authorized evidence exists
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
python3 -m py_compile scripts/verify_v1_phase5_evidence.py
bash -n scripts/verify-v1-phase5-evidence.sh scripts/validate-premerge.sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
git diff --check
```

## Acceptance Evidence

Repository-owned candidate evidence lives under `tests/evals/v1-phase5/` and
is enforced by `scripts/verify-v1-phase5-evidence.sh`. The accepted Phase 1-4
artifacts remain unchanged and their focused verifiers are rerun for
regression proof.

Current live-pilot evidence result: **blocked by absent owner authorization and
baseline evidence**. `tests/evals/v1-phase5/evidence/index.json` names the
blockers without inventing pilots. The expected exit 2 is a correct negative
result, not a Phase 5 failure and not acceptance.

Local candidate results on 2026-07-18:

- Phase 5 default verifier: **passed, 5/5 proof groups**. The group contains a
  test-only positive packet and rejects all ten required negative mutations.
- Dogfood-only verifier: **passed, 1/1 proof group** with the accepted Phase 4
  commit/blob/SHA provenance, only Phase 1 `target-owned-destination` paths,
  no rename/deletion, and three executed ordinary-task checks.
- Live pilot gate: **expected exit 2** with exactly two blockers: no owner
  authorization and no immutable revision/environment/signature/eligibility/
  intervention/baseline packet. This is the remaining gate, not a pass.
- Accepted Phase 1-4 regression verifiers: **10/10, 11/11, 11/11, and 10/10
  proof groups passed**.
- Rust workspace: **203 tests passed, 0 failed**; `cargo fmt --check` and
  workspace clippy with `-D warnings` passed offline.
- Documentation contract, Python compilation, shell syntax, JSON parsing,
  `git diff --check`, and the complete premerge repository contract passed.

Independent review may accept or reject the repository-owned candidate, but
only two complete real pilot packets can unblock Phase 5 acceptance.

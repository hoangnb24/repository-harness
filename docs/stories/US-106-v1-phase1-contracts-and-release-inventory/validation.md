# US-106 V1 Phase 1 Validation

Status: **Implemented / accepted**

## Proof Strategy

Phase 1 proof is contract proof, not runtime/release proof. Each group checks a
specific cause-and-effect boundary:

- schema/forbidden-field proof prevents V1 operational state expansion;
- grammar proof freezes a contract-only design authority, proves all named
  future Phase 2/4 entrypoints are absent, and prevents command leakage;
- ledger proof prevents authenticated but unauthorized paths entering core;
- V0 replay/snapshot proof prevents undocumented reader expansion;
- trust proof prevents small-order/zero-scalar forgery, unknown-key, one-key,
  crossover, replay, rollback, and revoked-key authorization;
- path proof prevents ADS/platform ambiguity and ancestor/final replacement;
- capture proof prevents source/WAL drift, source writes, and WAL-only data
  loss; and
- archive/policy proof prevents tampered/plaintext-by-default recovery evidence
  plus incomplete/stale monthly availability and premature Phase 8 eligibility.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Closed schema subset; RFC 8785 canonicalization; strict Ed25519 point/scalar verification; key IDs; exact bootstrap/grammar/implementation-binding arrays; rollback active-root-bundle binding; safe paths; forbidden fields; collision keys; freshness and exact-time decisions. |
| Integration | Current V0 installer/schema/workflow/build release inventory equality; future V1/bridge entrypoint and reserved-workflow absence; schemas 1–13 replay; parser-operation extraction; descriptor-anchored symlink/swap rejection; read-only DB/WAL/SHM capture; mutation/replacement negatives; standalone SQLite backup. |
| E2E | One focused script runs all nine proof groups and rejects committed negative fixtures; full premerge invokes the focused script. |
| Platform | Platform-independent path rules and five release labels are frozen; no new binary/platform runtime exists in Phase 1. |
| Performance | No product performance claim. Fixture sizes are bounded and verification uses temporary local files only. |
| Logs/Audit | Console test output only; no Harness state, trace, database, migration, or changeset operation. |

## Fixtures

- Three core roots plus three core release keys, and disjoint equivalent bridge
  keys, all 2-of-3 and unmistakably test-only.
- Valid core/bridge indexes, root bundles, high-water marks, exact rollback,
  a validly root-signed wrong-active-root-bundle rollback, revocation, root
  rotation, and signed monthly availability receipt.
- Identity/order-2 keys, zero-scalar and forged 2-of-3 envelopes, unknown-key,
  bad-signature, key-role/domain crossover, duplicate-member, Unicode
  re-encoding, freeze, wrong rollback, revoked signer, and rotation negatives.
- Valid/forbidden manifests, malformed and nested output schemas, exact
  bootstrap/command/implementation-binding/release inventory cases, reserved
  workflow state/path mismatches, unindexed paths, and all forbidden V0 core
  path classes.
- Safe paths, case/Unicode collision pairs, materialized symlink ancestors/final
  paths, ADS spellings, ancestor/final swaps, and in-place mutation.
- Exact migration bytes 001–013 and the full current operation/version matrix.
- A read-only raw main/WAL/SHM triplet where the committed proof row is absent
  from the main file and present after staged DB+WAL recovery; SHM is omitted
  from logical recovery input.
- Opaque encrypted-mode archive fixture and a one-byte tampered copy.
- Exact-seven-day positive receipt plus over-boundary, decreasing, wrong-month,
  missing-boundary, naive-time, incomplete-category, and missing-platform
  availability negatives.

## Commands

Run after implementation:

```bash
scripts/verify-v1-phase1-contracts.sh
bash -n scripts/verify-v1-phase1-contracts.sh
python3 -m py_compile scripts/verify_v1_phase1_contracts.py tests/fixtures/v1-phase1/generate.py
cargo fmt --all -- --check
cargo check --workspace --locked
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
git diff --check
scripts/validate-premerge.sh
```

The focused Phase 1 verifier does not invoke the V0 CLI. Its schema replay and
WAL recovery use isolated temporary fixture databases, never repository-root
`harness.db` or `.harness` state. Full `scripts/validate-premerge.sh`
intentionally invokes the repository's existing V0 CLI contract, smoke, and
installer tests with their isolated temporary state; this freezes current V0
behavior without treating it as a V1/bridge runtime or touching root Harness
state.

## Acceptance Evidence

Acceptance verified on 2026-07-17:

- `scripts/verify-v1-phase1-contracts.sh`: passed 9/9 proof groups.
- `bash -n scripts/verify-v1-phase1-contracts.sh`: passed with no output.
- `python3 -m py_compile` for the verifier and fixture generator: passed with
  no output using an isolated bytecode cache.
- At original Phase 1 acceptance,
  `python3 tests/fixtures/v1-phase1/generate.py --check` passed temporary
  regeneration. Decision 0014 subsequently removed required inputs; it is now
  historical provenance and exits 2 in a controlled way pointing to the
  cryptographic baseline verifier. The accepted evidence bytes remain frozen.
- `cargo fmt --all -- --check`: passed with no output.
- `cargo check --workspace --locked`: passed.
- `cargo test --workspace --locked`: passed, 92 tests total (90 V0 workspace
  tests plus 2 strict-Ed25519 helper tests); 0 failed, ignored, measured, or
  filtered out.
- `cargo clippy --workspace --all-targets --locked -- -D warnings`: passed.
- `git diff --check`: passed with no output.
- `scripts/validate-premerge.sh`: passed; it reran the 9 focused proof groups,
  all 92 Rust tests, and every repository bootstrap/protocol/installer/release/
  docs/task-authority contract, ending
  `pre-merge repository contract passed`.

Changed-scope inspection confirms no V1 or bridge binary, production key,
release/publish workflow, conversion write, root Harness state, or unrelated
artifact was created. Phase 1 is accepted, Phase 2 is ready, and Phases 2–8
remain unimplemented. The final commit hash is reported in the completion
response because it does not exist until this evidence record is committed.

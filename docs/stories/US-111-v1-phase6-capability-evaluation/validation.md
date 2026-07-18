# US-111 V1 Phase 6 Capability Evaluation Validation

Status: **Framework correction validated; live P0-P7 validation and Phase 6
acceptance not started**

## Proof Strategy

This slice can prove only that the authority, story packet, portable templates,
indexes, path ledger, phase statuses, and replay changesets are coherent and
preserve prior accepted bytes. It cannot prove that a capability improves an
agent outcome.

The proof ladder stops on the first failure:

1. Parse every changed JSON and JSONL record.
2. Run repository documentation and whitespace/diff checks.
3. Confirm required Decision 0015 custody/trust/identity/phase boundaries,
   including immutable warm masters, fresh paired derivatives, immediate
   pre-run verification, and evidence digest binding.
4. Confirm portable-template neutrality and target ownership.
5. Compare Phase 5 and US-110 bytes with exact starting commit `5d6e6bc`.
6. Confirm the changed-file set is a subset of the user-owned paths.
7. Rebuild/query only the isolated planning DB and confirm US-111 remains
   `in_progress` with no proof or acceptance booleans asserted.

## Framework Test Plan

| Layer | Cases |
| --- | --- |
| JSON | `path-dispositions.json` parses; each changeset line parses; headers and operations have expected versions. |
| Documentation | Required headings/links exist; template tables are structurally complete; no trailing whitespace. |
| Custody contract | Both lanes, pre-candidate capture, no live DB mutation, sealed raw-trio/standalone-master custody, fresh baseline/candidate derivatives from that same master, immediate pre-run identity verification, recovery-staging exclusion, digest binding, external signing, and Phase 7/8 closure are explicit. |
| Portability | Portable templates contain no pilot names, languages, package managers, or evaluator instructions; existing V0 Harness guidance is conditional and ordinary targets use target-owned proof/capability routes. |
| Preservation | Phase 5 files and every US-110 file match the starting commit byte-for-byte. |
| Durable replay | Intake UID `ink_e77c86ec00d11c619c8f9ffd282188b8` and US-111 replay into the isolated DB without touching live state. |
| Scope | No evaluator scripts/schemas, Rust, pilot/private evidence, keys, workflows, releases, or tags change. |

## Future Live-Card Acceptance

Future Phase 6 acceptance requires the fixed P0-P7 candidate results,
intervention totals, negative-condition report, and comparable baseline/
candidate report under Decision 0015. Each result must bind one externally
authenticated condition identity and an exact subject identity. Required
negative conditions fail the candidate; a prose explanation cannot waive them.

For every applicable warm pair, acceptance also requires:

1. The validated captured DB/WAL/SHM trio and standalone logical master are
   sealed immutable before either run.
2. Recovery-mutated staged files are excluded from condition-master and
   derivative custody.
3. Baseline and candidate use separate fresh derivatives created directly from
   the same sealed standalone master, never from one another.
4. Master and derivative identity/size/digests are verified immediately before
   each run.
5. Condition evidence binds the raw-trio/master/derivation digests, and subject
   evidence binds the derivative identity/digest and pre-run verification
   receipt.

At minimum:

- P3 proves a fresh agent resumes from a target-owned capsule whose exact next
  action and validation ladder are sufficient without human reconstruction.
- P4 proves a target-owned invariant check fails on a representative violation,
  guides bounded repair, and then passes.
- P5 proves the agent uses direct target feedback, with unavailable surfaces
  honestly recorded.
- P6 proves a repeated correction becomes a target-owned durable capability
  discovered by a held-out task without the original conversation.
- P7 proves target-owned gardening converges: a second equivalent-condition run
  finds no repeat drift or unrelated rewrite.

No row in this section is satisfied by the current docs commit.

## Commands

```bash
python3 -m json.tool release/contracts/v1/path-dispositions.json
python3 -c 'import json, pathlib; [json.loads(line) for path in pathlib.Path(".harness/changesets").glob("harness_v1_phase6_*.changeset.jsonl") for line in path.read_text().splitlines()]'
tests/docs/test-doc-contracts.sh
git diff --check
git diff --name-only 5d6e6bc
git diff --exit-code 5d6e6bc -- docs/stories/US-110-v1-dogfood-pilot-baselines
```

Changeset rebuild/query commands must set both `HARNESS_REPO_ROOT=$PWD` and
`HARNESS_DB_PATH=$PWD/.harness/refactor-plan.db`; they must never fall back to
root `harness.db`.

## Acceptance Evidence

Initial framework checks passed on 2026-07-18:

- The live documentation truth/link/authority contract passed.
- `path-dispositions.json` parsed, contained unique paths, and classified
  `docs/templates/agent-map.md` as `optional-v1` without claiming authenticated
  payload inclusion.
- Both Phase 6 JSONL files parsed and passed semantic changeset status. A fresh
  temporary rebuild applied 27 changesets and 106 operations; the replayed
  Intake row matched UID `ink_e77c86ec00d11c619c8f9ffd282188b8`, exact
  recorded fields, and notes. US-111 replayed as `in_progress` with unit,
  integration, E2E, and platform proof all unset/false.
- Existing template lines were preserved; Phase 6 additions were additive.
  Neutrality scans found no pilot, language, package-manager, or evaluator
  terms in the portable templates.
- Decision 0015 contained both custody lanes, pre-candidate capture,
  `condition_identity`/`subject_identity`, live-database and sensitive-byte
  prohibitions, external trust/signing, and Phase 7/8 closure.
- `git diff --check`, forbidden-path scope, and exact Phase 5/US-110 comparison
  against `5d6e6bc` passed.

These results accept only the documentation/capability framework. Live
candidate evidence remains pending external authorization/custody and is not
part of this slice.

Independent review then found that the warm lane did not yet close
condition-master derivation and that retained V0 Harness template guidance was
not explicitly conditional. The follow-up correction checks passed:

- Decision 0015 and US-111 now require the validated raw trio and standalone
  master to be sealed immutable, exclude recovery-mutated staging from master
  custody, create separate fresh baseline/candidate derivatives from the same
  master, and verify master plus derivative identity immediately before each
  run.
- Condition evidence binds raw-trio/master/derivation digests; subject evidence
  binds derivative identity/digest and the immediate pre-run verification
  receipt.
- `story.md` retains its headings, numeric example, and proof table while making
  the V0 durable-layer command and Harness Delta conditional. The high-risk
  exec plan retains its phases while routing the final phase to target-owned
  capability updates and Harness only when the target uses it.
- Documentation, JSON/JSONL, `git diff --check`, exact seven-file scope, and
  Phase 5/US-110 byte-preservation checks passed against the reviewed commit.

The bounded combined-stack regression repair then verified the Phase 6 bytes
against the earlier trust and recovery stack:

- The V0 installer manifest now carries `docs/templates/agent-map.md`, matching
  its `installer-manifest` ledger surface without adding it to the authenticated
  V1 core payload index.
- A new sequence-44 unsafe test-only release identity authenticates the current
  `decision.md` and Phase 6-expanded `story.md` bytes. Frozen Phase 1 fixture
  bytes remain unchanged, and historical lifecycle tests use a payload copy
  outside the Phase 1 fixture directory.
- The Phase 1 contract verifier, Phase 2 core suite/verifier, and Phase 3
  recovery verifier passed together; later Phase 4 and Phase 6 evidence checks
  also remained green.

This correction still supplies no live candidate card or Phase 6 acceptance.

## Gaps And Blockers

- No candidate subject, signed condition/result packet, live card outcome,
  intervention total, or comparison report exists in this slice.
- Phase 6 cannot be accepted until those external live records pass.
- Phase 7 remains closed on Phase 6 acceptance; Phase 8 remains closed on
  Phase 7 plus Decision 0012.

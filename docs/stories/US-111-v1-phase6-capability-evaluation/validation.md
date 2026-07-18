# US-111 V1 Phase 6 Capability Evaluation Validation

Status: **Framework validation pending completion; live P0-P7 validation and
Phase 6 acceptance not started**

## Proof Strategy

This slice can prove only that the authority, story packet, portable templates,
indexes, path ledger, phase statuses, and replay changesets are coherent and
preserve prior accepted bytes. It cannot prove that a capability improves an
agent outcome.

The proof ladder stops on the first failure:

1. Parse every changed JSON and JSONL record.
2. Run repository documentation and whitespace/diff checks.
3. Confirm required Decision 0015 custody/trust/identity/phase boundaries.
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
| Custody contract | Both lanes, pre-candidate capture, no live DB mutation, sensitive-byte exclusions, identity split, external signing, and Phase 7/8 closure are explicit. |
| Portability | Portable templates contain no pilot names, languages, package managers, evaluator instructions, or mandatory Harness ordinary-work command. |
| Preservation | Phase 5 files and every US-110 file match the starting commit byte-for-byte. |
| Durable replay | Intake UID `ink_e77c86ec00d11c619c8f9ffd282188b8` and US-111 replay into the isolated DB without touching live state. |
| Scope | No evaluator scripts/schemas, Rust, pilot/private evidence, keys, workflows, releases, or tags change. |

## Future Live-Card Acceptance

Future Phase 6 acceptance requires the fixed P0-P7 candidate results,
intervention totals, negative-condition report, and comparable baseline/
candidate report under Decision 0015. Each result must bind one externally
authenticated condition identity and an exact subject identity. Required
negative conditions fail the candidate; a prose explanation cannot waive them.

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

Framework checks passed on 2026-07-18:

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

## Gaps And Blockers

- No candidate subject, signed condition/result packet, live card outcome,
  intervention total, or comparison report exists in this slice.
- Phase 6 cannot be accepted until those external live records pass.
- Phase 7 remains closed on Phase 6 acceptance; Phase 8 remains closed on
  Phase 7 plus Decision 0012.

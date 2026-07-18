# P3 Final Target-Owned Resume Plan

## Goal

Revalidate CA-110 after the final trust and environment lock using the exact
credential-free target-native acceptance command, then leave an independently
usable validation report.

## Fixed Interruption Point

The first agent stops only after reading the governing instructions and CA-110
packet, comparing the final environment identity, running the metadata adapter
test alone, recording its exact result, and making no product/test change.

The fresh agent receives only the committed repository and this plan. Earlier
`rehearsal/P3/` artifacts are explicitly out of scope and may not be cited.

## Decisions

- Final environment digest:
  `1808dd68477e80c0fdb5bb04b4f1e99b280886432046022deb85772494af8256`.
- Packet-normalization annotation (added after the source run): the value above
  is the source-run legacy digest computed with a trailing newline. The
  verifier-canonical packet environment digest, computed without that trailing
  newline, is
  `1a2c1145670897c3d85a0fb9509704f3b70174a38fd0a6ae69e38d0b9f3c1f15`.
  No original plan decision or outcome changed.
- Exact original acceptance:
  `pnpm exec vitest run test/operational-metadata-adapter.spec.ts test/chat-contract.spec.ts test/mock-integration.spec.ts`.
- Use locked Node `22.22.3` and pnpm `10.30.1`; retain the Node engine mismatch.
- Credential-free tests only. Provider smoke, UAT, deployment, secrets, and
  database mutation are prohibited.
- A pass proves deterministic local behavior only; it cannot close CA-102 or
  provide owner sign-off.
- Fresh-agent edits are limited to this plan,
  `P3/fresh-agent-transcript.md`, and `P3/validation-report.md`.

## First-Agent Progress

- [x] Read governing Harness and CA-110 context.
- [x] Confirmed final trust/lock times precede this execution.
- [x] Confirmed ignored offline dependencies are present.
- [x] Ran focused metadata adapter proof from `2026-07-18T06:47:48Z` through
  `2026-07-18T06:47:53Z`: 1 file and 11 tests passed in 4.52 seconds, exit 0.
- [x] Stopped at fixed interruption point.

## Remaining Work For Fresh Agent

1. Read `AGENTS.md`, this final plan, final `environment.json`, and CA-110
   validation. Do not use `rehearsal/` results.
2. Recompute the final environment and catalog digests; record observed tool
   versions and current `HEAD`.
3. Run the exact original acceptance with the locked pnpm/Node path.
4. Record UTC start/end, exact argv, exit code, output/test counts, engine
   warning observation, and genuine blockers in `fresh-agent-transcript.md`.
5. Write `validation-report.md` with result, concrete cause/effect, and live
   provider/UAT gaps.
6. Mark the final checklist. Preserve a negative result; do not repair product
   code or ask the evaluator to reconstruct state.

## Final Checklist

- [x] Environment remained locked; no fresh-agent file change was made.
- [ ] Exact original acceptance was not completed/recorded before timeout.
- [x] Negative result recorded without evaluator reconstruction.
- [x] Live provider/UAT explicitly not attempted.

Final outcome: `failed` at `2026-07-18T06:57:17Z` after the fresh-agent
continuation exceeded the five-minute timebox.

# P3 Rehearsal Target-Owned Resume Plan

## Goal

Revalidate the existing CA-110 credential-free RAG readiness transition using
the locked repository and exact target-native acceptance command, then leave a
concise validation report.

## Fixed Interruption Point

The first agent stops immediately after all of the following are true:

1. Governing instructions and the CA-110 story packet have been read.
2. The environment identity has been compared with `environment.json`.
3. `test/operational-metadata-adapter.spec.ts` has been run alone and its exact
   result recorded below.
4. No product source or test file has been changed.

The fresh agent receives only the locked repository and this plan. The
evaluator must not reconstruct missing state.

## Decisions

- Use credential-free Vitest coverage only; live provider smoke and UAT are
  explicit non-goals.
- Preserve the locked Node `22.22.3` and pnpm `10.30.1` environment even though
  Node is below the package engine contract.
- The original target acceptance is exactly:
  `pnpm exec vitest run test/operational-metadata-adapter.spec.ts test/chat-contract.spec.ts test/mock-integration.spec.ts`.
- A passing test result proves only deterministic local behavior; it does not
  replace CA-102 live UAT or owner sign-off.
- The fresh agent may update only this plan, `P3/fresh-agent-transcript.md`, and
  `P3/validation-report.md`. It must not modify product code, tests, deployment,
  provider configuration, or secrets.

## First-Agent Progress

- [x] Read `AGENTS.md` and required Harness context.
- [x] Read the CA-110 overview, design, exec plan, and validation packet.
- [x] Confirmed offline dependencies are present.
- [x] Ran the focused metadata adapter test: 1 file and 11 tests passed in
  4.66 seconds, exit 0, from `2026-07-18T06:33:39Z` through
  `2026-07-18T06:33:46Z`.
- [x] Stopped at the fixed interruption point.

## Remaining Work For Fresh Agent

1. Re-read `AGENTS.md`, this plan, `environment.json`, and CA-110 validation.
2. Verify `git rev-parse 9be2b9b624f29c2c4f93bb576485fd8de2085af4^{commit}`
   resolves and record current `HEAD` without changing the environment.
3. Run the exact original acceptance command with the locked pnpm/Node path.
4. Record UTC start/end, ordered argv, exit code, engine warning, test counts,
   and any genuine failure in `fresh-agent-transcript.md`.
5. Write `validation-report.md` with scope, result, cause/effect, and explicit
   live-provider/UAT gap.
6. Mark the remaining checklist below. Do not repair product code if validation
   fails; preserve the negative result.

## Final Checklist

- [x] Environment digest unchanged.
- [x] Original acceptance command executed.
- [x] Final result recorded without evaluator reconstruction.
- [x] Live provider/UAT work explicitly not attempted.

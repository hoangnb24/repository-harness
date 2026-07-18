# P3 Durable Resume Plan

Status: `completed`

Fixed interruption point: `2026-07-18T07:12:57Z`, after reproducing and
diagnosing the seeded failure and before applying the repair.

Environment lock digest:
`b69c81a8ec42c39d80b0b9f814675646c4f1e39f688aa5a72bab01265e480dde`.

Packet-normalization annotation (added after the source run): the value above
is the source-run legacy digest computed with a trailing newline. The
verifier-canonical packet environment digest, computed without that trailing
newline, is
`b3a3067d79803aa6631ae7cd9f3424e13b102073bd9eb64123407a9ae43ef2dc`.
The original interruption facts and plan are unchanged.

## Goal

Restore correct dependency handling for resumed task subsets. A task whose
prerequisite is already represented by the restored checkpoint must not retain
that prerequisite in the subset plan, because it is not an executable task in
that subset.

## Seed identity

- Path: `benchmark/orchestrator/application/BuildRunExecutionPlan.ts`
- Starting-revision SHA-256:
  `3cebd00c347449352e0ff6c534425b5785acd760778d6e43f1761667e4d9a74b`
- Interrupted seeded SHA-256:
  `3e59a87c009150a7e8f3dc67a69d55726f4eda7ee25045a148dd70fb44bb9dd5`
- Seeded delta: the resumed task copy now preserves every original dependency
  instead of retaining only dependencies present in the selected subset.

## First-agent transcript

```text
$ npm test -- --run benchmark/orchestrator/test/build-run-execution-plan.test.ts
Test Files  1 failed (1)
Tests       1 failed | 3 passed (4)
Failure: drops dependencies satisfied by restored checkpoints from resumed subsets
Expected dependencies: []
Received dependencies: ["T2-crud-bookmarks"]
exit_code=1

$ rg --no-config -n "dependencies:" benchmark/orchestrator/application/BuildRunExecutionPlan.ts benchmark/orchestrator/test/build-run-execution-plan.test.ts
benchmark/orchestrator/application/BuildRunExecutionPlan.ts:21:        dependencies: task.dependencies,
benchmark/orchestrator/test/build-run-execution-plan.test.ts:81:    expect(execution.plan.tasks).toEqual([{ ...t3, dependencies: [] }]);
exit_code=0
```

## Decisions and cause/effect

1. Do not weaken or rewrite the test: it specifies the checkpoint-resume
   contract and its failure output directly identifies the regression.
2. Repair the application mapping, not the manifest or resume checkpoint data.
3. Filter each selected task's dependencies against the IDs selected for this
   execution subset. This keeps dependencies that will run in the subset and
   drops dependencies already satisfied outside it.
4. Keep the diff limited to the seeded line. The seed was deliberately
   reversible and the starting revision contains the intended implementation.
5. Validate first with the focused resume-plan test, then the locked P3 command
   `npm test -- --run benchmark/orchestrator/test`, then `npm run build` and
   `git diff --no-ext-diff --check`.

Cause and effect: preserving `task.dependencies` leaves `T2-crud-bookmarks` on a
T3-only resumed subset even though the restored T2 checkpoint satisfies it.
Filtering against `selectedTaskIds` removes that stale edge while preserving
edges between tasks that are actually selected.

## Progress

- Required repository and high-risk benchmark context read.
- Native Harness matrix/tool queries attempted and blocked by absent CLI.
- Seed applied and digest captured.
- Focused failure reproduced and diagnosed.
- Repair applied: resumed task dependencies are filtered to the selected
  execution subset.
- Focused resume-plan test passed: 1 file, 4 tests.
- Locked P3 acceptance suite passed: 19 files, 90 tests.
- TypeScript build passed.
- `git diff --no-ext-diff --check` passed.
- Final source SHA-256:
  `3cebd00c347449352e0ff6c534425b5785acd760778d6e43f1761667e4d9a74b`
  (matches the starting-revision digest).

## Resume checklist (completed)

1. Inspect this plan and the named source/test only; no evaluator reconstruction
   is available.
2. Apply the smallest source repair described above.
3. Run the focused test, the locked P3 acceptance command, the build, and the
   whitespace check.
4. Update this plan from `interrupted` to `completed`, append exact validation
   results, and create `resume-transcript.md` with ordered commands, exit codes,
   changed paths, final diff, and final source digest.
5. Do not change evidence outside `cards/P3`, do not commit, and do not push,
   deploy, mutate remotes, generate keys, or sign.

## Resume result

Completed and finally verified at `2026-07-18T07:16:37Z`. The source-only
repair changed the seeded line from preserving all dependencies to retaining
only dependencies whose IDs are present in `selectedTaskIds`. This makes a
T3-only resumed subset drop its checkpoint-satisfied T2 edge while preserving
edges between tasks selected to run together. Full command evidence is in
`resume-transcript.md`.

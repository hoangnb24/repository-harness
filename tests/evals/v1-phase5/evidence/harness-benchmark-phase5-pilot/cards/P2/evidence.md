# P2 Ordinary Small Task Evidence

Outcome: `passed`.

Prompt: update the stale `src/index.ts` task-range comment from T1-T6 to the
manifest's actual T1-T12 range, follow repository instructions, and run the
named target-native build check. Do not invoke a V1 core command or create a
Harness-only durable plan.

## Ordered transcript

```text
$ rg --no-config -n "tasks T1-T12" src/index.ts
3:// The agent will build this out across tasks T1-T12
exit_code=0

$ npm run build

> harness-benchmark@1.0.0 build
> tsc

exit_code=0

$ git diff --no-ext-diff --name-only -- src/index.ts
src/index.ts
exit_code=0
```

Core-command count in this task transcript: `0`.

Changed path: `src/index.ts`.

Diff:

```diff
-// The agent will build this out across tasks T1-T6
+// The agent will build this out across tasks T1-T12
```

Cause and effect:

1. The manifest contains T1-T12, while the entrypoint comment named only T1-T6.
2. Updating the comment aligns repository-native guidance without changing
   runtime behavior.
3. The locked `npm run build` command exited 0, so the comment-only repair did
   not regress TypeScript compilation.
4. No V1 command or Harness-only plan entered the task transcript.

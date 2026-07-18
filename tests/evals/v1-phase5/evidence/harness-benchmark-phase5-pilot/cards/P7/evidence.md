# P7 Gardening Convergence Evidence

Outcome: `passed`.

Bounded scope: trailing-whitespace maintenance in `src/index.ts` only.

Trigger and locked acceptance:
`git diff --no-ext-diff --check`.

The existing P2 content change from T1-T6 to T1-T12 is outside gardening scope
and must be preserved. The reversible gardening seed added two trailing spaces
to that already-changed line.

## Seed trigger

At `2026-07-18T07:31:45Z`:

```text
$ shasum -a 256 src/index.ts
bfcc1d4ecabeede61e870af80aca081accc2f97f5d0ec0bd8dc9e34b650af31b  src/index.ts
exit_code=0

$ rg --no-config -n '[[:blank:]]+$' src/index.ts
3:// The agent will build this out across tasks T1-T12[space][space]
exit_code=0

$ git diff --no-ext-diff --check
src/index.ts:3: trailing whitespace.
+// The agent will build this out across tasks T1-T12[space][space]
exit_code=2
```

## Gardening run 1

Relevant repair: remove only the two seeded trailing spaces.

Before inventory:
`src/index.ts bfcc1d4ecabeede61e870af80aca081accc2f97f5d0ec0bd8dc9e34b650af31b`.

At `2026-07-18T07:31:59Z`:

```text
$ rg --no-config -n '[[:blank:]]+$' src/index.ts
exit_code=1

$ git diff --no-ext-diff --check
exit_code=0

$ shasum -a 256 src/index.ts
3de9cdeb777cff5c3884c0395f0209198623a43073ed50840a90ed845ff87981  src/index.ts
exit_code=0
```

After inventory:
`src/index.ts 3de9cdeb777cff5c3884c0395f0209198623a43073ed50840a90ed845ff87981`.

The only run-1 delta was removal of the bounded trailing whitespace; the P2
task-range correction remained intact.

## Gardening run 2

Run 2 used the same bounded path, trigger, and validation with no new seed or
condition change.

At `2026-07-18T07:32:09Z`:

```text
$ shasum -a 256 src/index.ts
3de9cdeb777cff5c3884c0395f0209198623a43073ed50840a90ed845ff87981  src/index.ts
exit_code=0

$ rg --no-config -n '[[:blank:]]+$' src/index.ts
exit_code=1

$ git diff --no-ext-diff --check
exit_code=0

$ shasum -a 256 src/index.ts
3de9cdeb777cff5c3884c0395f0209198623a43073ed50840a90ed845ff87981  src/index.ts
exit_code=0

$ npm run build
> tsc
exit_code=0
```

Run-2 before and after digests are identical, so the second run found no repeat
drift and made no change. The locked validation and TypeScript build both pass.
The two `gardening review` events are recorded separately in the intervention
log; no evaluator cleanup is hidden.

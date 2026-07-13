# Validation

## Proof Strategy

Each workstream adds a negative regression that reproduces the prior failure and
a positive regression that preserves intended behavior. The final wrapper runs
all focused regressions plus the existing Rust, replay, installer, release, and
documentation contracts.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Lifecycle target validation, matrix filters, coherence tuple evaluation, context/request classification. |
| Integration | Completion bypass rejection, fresh-proof completion, SQLite query-only enforcement, schema/version drift reporting. |
| E2E | Fresh source bootstrap, focused agent intake, read-only audit, normal implementation task, stale-runtime recovery. |
| Platform | Bash and PowerShell shim parity; native CLI help/version/coherence behavior. |
| Performance | Default intake context and matrix output remain bounded relative to the previous full bootstrap. |
| Logs/Audit | Rejected bypasses create no story mutation or semantic changeset; read-only workflows create no Harness rows. |

## Fixtures

- Fresh schema-13 database with one planned story.
- Story with a passing verify command and one with no command.
- Database copy containing a mutation sentinel table.
- Matching and mismatching executable/release/schema tuples.
- Canonical instruction block rendered through fresh, Bash refresh, PowerShell
  refresh, and Claude import paths.
- Representative tiny/read-only, normal change, high-risk change, and missing-tool
  task fixtures.

## Commands

Local proof, pull-request CI, release verification, and the durable US-101
verification command now share one entrypoint:

```bash
scripts/validate-premerge.sh
```

The wrapper runs Rust formatting, all 90 tests, clippy, revision/schema and
bootstrap coherence, ownership negatives, protocol smoke, installer modes,
documentation truth, representative task effects, release contracts, and
`git diff --check`. Pull requests additionally run the PowerShell installer
fixture on `windows-latest`.

## Acceptance Evidence

- Main synchronized to `3ed8bb6`; release CLI rebuilt as `0.1.15`.
- Local database migrated from schema 10 to schema 13 and contract state became
  `current`.
- `725a9ea` rejects direct `implemented` updates, preserves rejected DB/log
  state, and requires `story complete` for interactive completion.
- `153a76f` opens SQL queries physically read-only and denies DML, mutating
  pragmas, ATTACH, and WAL checkpoint effects while preserving SELECT/CTE and
  safe pragma reads.
- `acba26e` adds CLI/pin/schema coherence, consumer bootstrap, fail-closed core
  ownership checks, and focused matrix views. The current active summary fell
  from 48,082 bytes to 819 bytes while the unfiltered output remained
  byte-for-byte compatible.
- `fad321a` makes response-only requests read-only, keeps tiny-change default
  Harness context below 8 KiB, and sources root/Bash/PowerShell/Claude behavior
  from canonical instruction blocks.
- `6bd7bb0` adds the shared pre-merge/release wrapper, live-document contract,
  Ubuntu PR gate, Windows installer job, and deterministic task-effect suite.
- `story verify US-101` and proof-backed `story complete US-101` both reran the
  wrapper successfully; the final local verification result is `pass` at
  `2026-07-13 03:12:13`. Detailed trace `#29` meets the high-risk 3/3 tier.
- The ignored local source database is schema-current but still contains the
  pre-cutover Symphony epoch. `verify-core-state-ownership.sh` now refuses that
  state with the exact leaked story IDs instead of presenting it as coherent.
  It was not destructively rewritten because no verified replacement epoch is
  available in this checkout.
- Proof columns are unit/integration/E2E/platform `yes`. GitHub Actions run
  `29221331817` passed both the Ubuntu repository contract and the hosted
  Windows PowerShell installer fixture; the first Windows run also caught and
  proved the `$LASTEXITCODE` versus `$?` fixture correction in `0db1de0`.

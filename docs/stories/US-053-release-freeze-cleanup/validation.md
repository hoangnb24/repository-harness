# Validation

## Proof Strategy

Use documentation/static checks for release wording and deployment boundary,
then run the existing v0.2 regression gates to prove no behavior or artifact
contract changed.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Full pytest regression suite covers unchanged profiler behavior. |
| Integration | `make demo-small`, `make demo-full`, package audit, benchmark smoke, and optional connector smokes. |
| E2E | Existing dashboard Playwright E2E through `npm run test:e2e:dashboard`. |
| Platform | `node --check web/app.js`, static Vercel boundary docs/config, local runner docs on `127.0.0.1`. |
| Performance | `make benchmark-small`. |
| Logs/Audit | Harness story verify, decision verify, audit, trace scoring, and final git status classification. |

## Fixtures

- Synthetic demo dataset under `data/demo_small`.
- Optional local Postgres fixture from `VSF_POSTGRES_TEST_URL`.
- Optional local MySQL/MariaDB fixture from `VSF_MYSQL_TEST_URL`.
- Existing static web runner/dashboard fixtures and generated artifacts.

## Commands

```text
git status --short
git diff --check
node --check web/app.js
npm run test:e2e:dashboard
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py
vsf-profiler doctor
make demo-small
make demo-full
make benchmark-small
make postgres-smoke
make mysql-smoke
scripts/bin/harness-cli story verify US-053
scripts/bin/harness-cli decision verify 0023
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `git diff --check` -> passed.
- `node --check web/app.js` -> passed.
- `scripts/bin/harness-cli story verify US-053` -> passed.
- `scripts/bin/harness-cli decision verify 0023` -> passed.
- `.venv/bin/pytest -q` -> 76 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
  -> passed.
- `npm run test:e2e:dashboard` -> 1 passed.
- `vsf-profiler doctor` -> required checks passed; optional Postgres, MySQL,
  and OpenAI env checks skipped without configured local URLs/keys; PDF, Node,
  and Playwright checks passed.
- `make demo-small` -> passed with 15 issues.
- `make demo-full` -> passed; wrote package index, export manifest,
  `analysis_report.pdf`, zip archive, artifact audit status `passed` with 0
  violations, and Playwright dashboard E2E passed.
- `make benchmark-small` -> passed and wrote
  `outputs/benchmark_ci/run/performance_guard_report.json` with status
  `passed`.
- `make postgres-smoke` -> 1 skipped because no local Postgres URL/capability
  is configured.
- `make mysql-smoke` -> 1 skipped because no local MySQL/MariaDB URL/capability
  is configured.
- Generated `.DS_Store`, pytest, Ruff, Python bytecode, and Playwright result
  caches were cleaned. Generated local data/output directories remain outside
  release scope through `.gitignore`; release-worthy source/docs/tests remain
  preserved.

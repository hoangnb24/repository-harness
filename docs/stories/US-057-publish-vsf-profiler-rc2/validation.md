# Validation

## Proof Strategy

Prove the release by validating the product checkout after copying, then verify
that the public GitHub tag and prerelease exist and link to the expected repo
state.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Full pytest in the product repo. |
| Integration | `make demo-full` in the product repo writes canonical artifacts and package output. |
| E2E | `npm run test:e2e:dashboard` through `make demo-full` and/or direct run. |
| Platform | `node --check web/app.js`, Ruff, `gh release view`, README/release URL checks. |
| Performance | Existing benchmark is not mandatory for this publish slice because US-055/US-056 were already release-gated. |
| Logs/Audit | Harness story verify, audit, and trace. |

## Fixtures

- Existing demo fixture under `data/demo_small`.
- Product checkout `/Users/jin/Auto-data-profilling-and-smart-eda-tools`.
- GitHub repo `Tan-Long/Auto-data-profilling-and-smart-eda-tools`.

## Commands

```text
node --check web/app.js
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py
npm run test:e2e:dashboard
make demo-full
gh release view vsf-profiler-v0.2.0-rc2 --repo Tan-Long/Auto-data-profilling-and-smart-eda-tools
scripts/bin/harness-cli story verify US-057
scripts/bin/harness-cli audit
```

## Acceptance Evidence

| Check | Result |
| --- | --- |
| Product install | `.venv/bin/python -m pip install -e ".[dev]"` -> installed `vsf-profiler==0.2.0rc2` |
| Node syntax | `node --check web/app.js` -> passed |
| Product full pytest | `.venv/bin/pytest -q` -> 79 passed, 3 skipped |
| Product Ruff | `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py` -> passed |
| Product dashboard E2E | `npm run test:e2e:dashboard` -> 1 passed |
| Product release demo | `PATH="/Users/jin/Auto-data-profilling-and-smart-eda-tools/.venv/bin:$PATH" make demo-full` -> passed with artifact audit and Playwright E2E |
| Commit/tag | Product repo commit `ac2ce0f`; annotated tag `vsf-profiler-v0.2.0-rc2` pushed |
| GitHub prerelease | `gh release view vsf-profiler-v0.2.0-rc2` -> `isPrerelease=true`, `isDraft=false` |
| README/release links | GitHub API confirmed remote README links to the rc2 release and `docs/releases/v0.2.0-rc2.md`; rendered README HTML contains both links |

The first unqualified `make demo-full` attempt failed because the shell found a
different checkout's `vsf-profiler` and system `python3`. The documented
activated-venv equivalent with the product `.venv/bin` first on `PATH` passed.

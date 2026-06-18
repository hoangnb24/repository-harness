# US-060 Publish VSF Data Profiler v0.2.0-rc3

## Status

implemented

## Lane

normal

## Product Contract

Publish a new public VSF Data Profiler prerelease after US-058 and US-059 so
demo users receive the Generated Results preview and reliable local DBML
diagram preview without changing backend routes, CLI behavior, artifact names,
or artifact contracts.

## Relevant Product Docs

- `README.md`
- `docs/releases/v0.2-rc.md`
- `docs/releases/v0.2.0-rc3.md`
- `docs/product/vsf-data-profiler.md`
- `docs/TEST_MATRIX.md`

## Acceptance Criteria

- Product repo `main` includes the US-058 and US-059 UI, docs, and test deltas.
- Version metadata is bumped from `0.2.0rc2`/`0.2.0-rc2` to
  `0.2.0rc3`/`0.2.0-rc3`.
- Git tag `vsf-profiler-v0.2.0-rc3` is pushed.
- GitHub prerelease `VSF Data Profiler v0.2.0-rc3` is published with release
  notes covering Generated Results preview, reliable local DBML diagram
  preview, dbdiagram.io as secondary, no backend/artifact contract changes, and
  validation proof.

## Design Notes

- Commands: product release checkout at
  `/Users/jin/Auto-data-profilling-and-smart-eda-tools`.
- GitHub release:
  `https://github.com/Tan-Long/Auto-data-profilling-and-smart-eda-tools/releases/tag/vsf-profiler-v0.2.0-rc3`.
- Commit: `915dbd4 chore: release vsf profiler v0.2.0-rc3`.
- Tag: `vsf-profiler-v0.2.0-rc3`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Product full pytest passes. |
| Integration | Product Ruff and artifact audit pass. |
| E2E | Playwright dashboard E2E passes. |
| Platform | Product `make demo-full`, tag push, and GitHub prerelease verification pass. |
| Release | Remote README, release note, and annotated tag dereference verify. |

## Harness Delta

- Durable intake recorded as change request #46.
- Durable story recorded as US-060.
- Test matrix updated with rc3 publish evidence.

## Evidence

- `.venv/bin/python -m pip install -e ".[dev]"` -> installed
  `vsf-profiler==0.2.0rc3`.
- `node --check web/app.js` -> passed.
- Focused product suite
  `.venv/bin/pytest -q tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py`
  -> 15 passed.
- `.venv/bin/pytest -q` -> 79 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
  -> all checks passed.
- `npm run test:e2e:dashboard` -> 1 passed with package version
  `0.2.0-rc3`.
- `PATH="$PWD/.venv/bin:$PATH" make demo-full` -> doctor ok, demo/package/PDF
  outputs written, artifact audit passed with 0 violations, bundled Playwright
  -> 1 passed.
- `git diff --check` -> passed.
- Product commit pushed: `915dbd4`.
- Annotated tag pushed: `vsf-profiler-v0.2.0-rc3`, dereferenced to
  `915dbd4d07ce186676ea2542b9cf273160239f9e`.
- GitHub prerelease published and verified:
  `https://github.com/Tan-Long/Auto-data-profilling-and-smart-eda-tools/releases/tag/vsf-profiler-v0.2.0-rc3`.

# US-063 Publish VSF Data Profiler v0.2.0-rc5

## Status

implemented

## Lane

normal

## Product Contract

Publish the current demo-facing dashboard Graph declutter to the public product
repository as `vsf-profiler-v0.2.0-rc5`. The release must preserve backend
routes, CLI behavior, artifact names, and artifact contracts while updating
version metadata, public release notes, README links, validation evidence, tag,
and GitHub prerelease.

## Relevant Product Docs

- `README.md`
- `docs/releases/v0.2-rc.md`
- `docs/releases/v0.2.0-rc5.md`
- `docs/product/vsf-data-profiler.md`
- `docs/TEST_MATRIX.md`

## Acceptance Criteria

- Product repo `main` includes the US-061/US-062 web UI, docs, and test deltas.
- Version metadata is bumped to `0.2.0rc5` for Python and `0.2.0-rc5` for Node.
- Git tag `vsf-profiler-v0.2.0-rc5` is pushed.
- GitHub prerelease `VSF Data Profiler v0.2.0-rc5` is published with release
  notes covering progressive graph disclosure, low-noise overview,
  Focus/Full modes, opt-in columns/runtime/artifacts, cleaner relationship
  default, no backend/artifact contract changes, and validation proof.

## Design Notes

- Commands: product release checkout at
  `/Users/jin/Auto-data-profilling-and-smart-eda-tools`.
- GitHub release:
  `https://github.com/Tan-Long/Auto-data-profilling-and-smart-eda-tools/releases/tag/vsf-profiler-v0.2.0-rc5`.
- Remote baseline verified before work: GitHub releases existed for rc1-rc3;
  rc4 was not present remotely at publish time.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Product focused and full pytest pass. |
| Integration | Product Ruff and artifact audit pass. |
| E2E | Playwright dashboard E2E passes. |
| Platform | Product `make demo-full`, tag push, and GitHub prerelease verification pass. |
| Release | Remote README, release note, and annotated tag dereference verify. |

## Harness Delta

- Durable intake recorded as change request #49.
- Durable story recorded as US-063.

## Evidence

- `.venv/bin/python -m pip install -e ".[dev]"` in the product repo ->
  installed `vsf-profiler==0.2.0rc5`.
- `node --check web/app.js` -> passed.
- `.venv/bin/pytest -q tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py`
  -> 15 passed.
- `npm run test:e2e:dashboard` -> 1 passed with package version
  `0.2.0-rc5`.
- `.venv/bin/pytest -q` -> 79 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
  -> all checks passed.
- `PATH="$PWD/.venv/bin:$PATH" make demo-full` -> doctor ok, demo/package/PDF
  outputs written, artifact audit passed with 0 violations, bundled Playwright
  -> 1 passed.
- `git diff --check` -> passed.
- Product commit pushed: `8892245`.
- Annotated tag pushed: `vsf-profiler-v0.2.0-rc5`, dereferenced remotely to
  `88922459110ed8e90de128653c5c9086fdb334ae`.
- GitHub prerelease published and verified:
  `https://github.com/Tan-Long/Auto-data-profilling-and-smart-eda-tools/releases/tag/vsf-profiler-v0.2.0-rc5`.
- Remote README and `docs/releases/v0.2.0-rc5.md` verified through the GitHub
  API.
- `scripts/bin/harness-cli story verify US-063` -> passed.

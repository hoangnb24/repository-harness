# US-053 Goal: Release Freeze, Repo Hygiene, and Deployment Boundary Cleanup

## Objective

Prepare the current VSF Data Profiler feature set for a clean v0.2 local
release candidate by cleaning release metadata and docs, clarifying deployment
boundaries, and proving final local demo gates. Do not add new product
features.

## Context To Read First

- `AGENTS.md`
- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/product/vsf-data-profiler.md`
- `docs/releases/v0.2-rc.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0009-static-web-workspace.md`
- `docs/decisions/0011-local-web-runner-boundary.md`
- `docs/decisions/0022-mysql-pdf-export-boundary.md`
- `Makefile`
- `pyproject.toml`
- `vercel.json`
- `.vercelignore`
- `.gitignore`
- `scripts/bin/harness-cli query matrix`
- `git status --short`

## Scope

- Create US-053 story/evidence and a decision if deployment or release boundary
  wording changes materially.
- Update README title and wording so the product is no longer framed as only an
  MVP when it is now a v0.2 local release candidate.
- Align `pyproject.toml` version and release wording with v0.2 RC if repo
  convention allows it.
- Update release docs so US-052/MySQL/PDF is the latest release gate, while
  US-050 remains the original release-candidate hardening base.
- Clarify Vercel in README, release docs, and product docs:
  - Vercel deployment is static preflight UI only.
  - Vercel does not run Python/DuckDB backend jobs.
  - Full profiling/dashboard jobs require local `vsf-profiler web` on
    `127.0.0.1`.
- Align demo docs:
  - canonical local release demo is `make demo-full`;
  - browser backend demo is `make web-runner` and `http://127.0.0.1:8765`;
  - Olist, Postgres, and MySQL smokes are optional capability demos.
- Audit working tree and classify tracked/release-worthy files versus
  generated/local files.
- Tighten `.gitignore` only for clearly generated local files such as
  `.DS_Store`, caches, local outputs, and private environment state.
- Ensure generated demo outputs, local Vercel state, `.env`, and secrets are not
  part of release scope.
- Leave implemented product source, tests, and docs intact.
- Record final Harness trace and update matrix evidence.

## Constraints

- Do not add new product features.
- Do not implement a hosted backend.
- Do not change existing artifact names.
- Do not refactor core profiler behavior.
- Do not rework PDF generation or dashboard features.
- Do not commit or push unless explicitly asked.
- Do not delete user-created files unless they are clearly generated local
  artifacts such as `.DS_Store`, cache folders, or test output.
- Do not remove implemented source, tests, or docs just because they are
  currently untracked.
- If a file's release status is ambiguous, document it and pause instead of
  deleting it.

## Operating Rules

- Prefer documentation and release hygiene changes over code changes.
- Keep changes additive and release-focused.
- Use the Harness CLI for intake, story, decision, trace, and audit records.
- Preserve the current local-first security boundary:
  - hosted Vercel static preflight only;
  - local `127.0.0.1` backend for real profiling jobs;
  - no hosted database/file-processing worker in this release.

## Out Of Scope

- New database connectors.
- Hosted backend implementation.
- Auth, storage, queues, or multi-user deployment.
- Public SaaS deployment architecture beyond documenting the boundary.
- Core profiling algorithm changes.
- Package/PDF/dashboard feature expansion.

## Validation Loop

During work:

- `git status --short`
- `git diff --check`
- `node --check web/app.js` if web docs/config are touched
- focused docs/static checks if available

Final proof:

- `.venv/bin/pytest -q`
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
- `node --check web/app.js`
- `npm run test:e2e:dashboard`
- `vsf-profiler doctor`
- `make demo-small`
- `make demo-full`
- `make benchmark-small`
- `make postgres-smoke`, passing or clean-skipping according to environment
- `make mysql-smoke`, passing or clean-skipping according to environment
- `scripts/bin/harness-cli story verify US-053`
- `scripts/bin/harness-cli decision verify <id>` if a decision is created
- `scripts/bin/harness-cli audit`

## Done When

- README, product docs, and release docs clearly describe v0.2 local RC scope.
- Vercel is explicitly documented as static preflight only.
- The local backend location and command are unambiguous.
- Demo paths are consistent across README and release docs.
- Working tree hygiene is improved and generated/private files are ignored or
  removed from release scope.
- No implemented source, tests, or docs are lost.
- Final gates pass, or optional smokes clean-skip with explicit messages.
- Harness story, matrix, trace, and audit evidence are updated.

## Pause If

- Version bump conflicts with repo convention.
- Any cleanup would require deleting ambiguous user-created files.
- Vercel is intended to become a real hosted backend in this release.
- Final gates fail for reasons unrelated to release cleanup.

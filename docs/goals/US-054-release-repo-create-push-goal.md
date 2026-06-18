# US-054 Goal: Create Product GitHub Repo and Push v0.2.0-rc1

## Objective

Create a new GitHub repository named `Auto-data-profilling-and-smart-eda-tools`
for the VSF Data Profiler product, copy only release-worthy product files out of
the Harness workspace, validate the release in the new repo, commit, tag, and
push `v0.2.0-rc1` there.

## Context To Read First

- `AGENTS.md`
- `README.md`
- `docs/releases/v0.2-rc.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/stories/US-053-release-freeze-cleanup/overview.md`
- `docs/decisions/0023-vercel-static-local-runner-release-boundary.md`
- `.gitignore`
- `.vercelignore`
- `Makefile`
- `pyproject.toml`
- `package.json`
- `playwright.config.js`
- `vercel.json`
- `git status --short`
- `git branch --show-current`
- `git remote -v`
- `gh auth status` if `gh` is available
- `scripts/bin/harness-cli query matrix`

## Target Repository

- Repository name: `Auto-data-profilling-and-smart-eda-tools`
- GitHub owner: use the authenticated GitHub account or ask/pause if owner is
  ambiguous.
- Do not push the product release to `repository-harness`.
- Recommended local sibling path:
  `/Users/jin/Auto-data-profilling-and-smart-eda-tools`

## Scope

- Create a clean product repo outside the Harness workspace.
- Initialize it as a new git repository if it does not already exist.
- Create the GitHub repo `Auto-data-profilling-and-smart-eda-tools` if it does
  not already exist.
- Copy release-worthy product files from `/Users/jin/repository-harness` into
  the new repo:
  - `src/`
  - `tests/`
  - `web/`
  - `templates/`
  - `examples/`
  - `scripts/benchmark_large_dataset.py`
  - `scripts/verify_openai_smoke.py`
  - `scripts/verify_vsf_artifacts.py`
  - `README.md`
  - `pyproject.toml`
  - `Makefile`
  - `.env.example`
  - `.gitignore`
  - `.vercelignore`
  - `vercel.json`
  - `package.json`
  - `package-lock.json`
  - `playwright.config.js`
  - product, architecture, demo, release, decision, story, matrix, and goal docs
    that document VSF Data Profiler release evidence.
- Exclude Harness-only implementation internals unless the docs are needed as
  release evidence:
  - do not copy `harness.db`;
  - do not copy Harness Rust/tooling source unless explicitly needed;
  - do not copy `scripts/bin/harness-cli`;
  - do not copy `.vercel/`, `.env`, `outputs/`, generated `data/`, caches,
    `.DS_Store`, local scratch folders, or secrets.
- Preserve local-first release boundary docs:
  - Vercel is static preflight only;
  - full profiler/dashboard jobs require local `vsf-profiler web` on
    `127.0.0.1`.
- Run release validation from inside the new repo.
- Commit the release.
- Tag the commit as `vsf-profiler-v0.2.0-rc1`.
- Push the new repo's `main` branch and tag to GitHub.

## Constraints

- Do not force-push.
- Do not push to `hoangnb24/repository-harness` or any Harness framework repo.
- Do not commit secrets, `.env`, `.vercel/`, local generated outputs, cache
  folders, `.DS_Store`, or raw smoke/demo outputs.
- Do not delete the original Harness workspace.
- Do not remove source/tests/docs from the original workspace.
- Do not change product behavior unless a validation gate exposes a small
  release-blocking issue.
- If the GitHub owner or repo visibility is unclear, pause before creating the
  remote.
- If the target repo already exists and has unrelated commits, pause before
  overwriting or force-pushing.

## Operating Rules

1. Inspect source workspace status and ignored files.
2. Create or clean only the new product repo directory, never the Harness repo.
3. Copy files using explicit allow-lists or rsync exclude rules.
4. Inspect the new repo with `git status --short`, `find`, and targeted grep for
   secrets before staging.
5. Stage intentionally.
6. Review staged changes with `git diff --cached --stat` and targeted checks
   for sensitive files.
7. Run validation from the new repo.
8. Commit with:
   `chore: release vsf profiler v0.2.0-rc1`
9. Create tag:
   `vsf-profiler-v0.2.0-rc1`
10. Push `main` and the tag to the new GitHub repo without force.
11. Record Harness trace in the source Harness workspace with the new repo URL,
    commit SHA, tag, validation results, and any clean skips.

## Validation Loop

Before commit, from the new product repo:

- `git status --short`
- `git diff --check`
- `.venv/bin/pytest -q` or `python -m pytest -q` after installing dev deps
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
- `node --check web/app.js`
- `npm run test:e2e:dashboard`
- `vsf-profiler doctor`
- `make demo-small`
- `make demo-full`
- `make benchmark-small`
- `make postgres-smoke`, passing or clean-skipping according to environment
- `make mysql-smoke`, passing or clean-skipping according to environment

After commit and tag:

- `git status --short`
- `git log --oneline -1`
- `git tag --points-at HEAD`
- `git remote -v`
- `git push origin main`
- `git push origin vsf-profiler-v0.2.0-rc1`
- `git ls-remote --heads origin main`
- `git ls-remote --tags origin vsf-profiler-v0.2.0-rc1`

Back in the Harness workspace:

- `scripts/bin/harness-cli trace ...`
- `scripts/bin/harness-cli audit`

## Done When

- New GitHub repo `Auto-data-profilling-and-smart-eda-tools` exists.
- Product release files are copied into the new repo.
- Harness-only/generated/private files are not committed.
- Release validation passes, with optional DB smokes passing or clean-skipping.
- `main` is pushed to the new GitHub repo.
- Tag `vsf-profiler-v0.2.0-rc1` is pushed to the new GitHub repo.
- Final answer reports:
  - repo URL;
  - commit SHA;
  - tag;
  - validation summary;
  - skipped optional checks, if any.

## Pause If

- GitHub owner cannot be determined.
- GitHub repo creation requires confirmation of owner or visibility.
- Target repo already exists with unrelated history.
- A secret or credential appears in the new repo status/diff.
- Required validation fails.
- Push is rejected because remote has unexpected commits.

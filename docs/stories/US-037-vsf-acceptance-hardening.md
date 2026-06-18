# US-037 VSF Acceptance Hardening

## Status

implemented

## Lane

normal

## Product Contract

Perform an end-to-end acceptance pass for VSF Data Profiler against the DBML
multi-CSV streaming EDA contract. Fix only small gaps found in docs, CLI UX,
artifact contracts, tests, or demo validation. Do not add new product scope.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0008-vsf-profiler-python-cli-stack.md`

## Acceptance Criteria

- The derived product contract is compared against the current implementation.
- Default `make demo-small` passes and produces the full deterministic artifact
  set.
- `vsf-profiler run ... --use-llm --llm-provider fake` passes and produces the
  optional L4 artifact set.
- Artifact lists are checked for deterministic and optional L4 runs.
- Production code has no unbounded `pd.read_csv` or direct `.fetchdf()` outside
  the bounded guard.
- README, architecture, product contract, and test matrix are synchronized.
- An acceptance report records pass/gap status and any backlog-only gaps.

## Design Notes

- Commands: use existing CLI and Make targets.
- Queries: no product-query changes.
- API: no new API shape beyond acceptance docs if no gap is found.
- Tables: no schema changes.
- Domain rules: no new product behavior; only acceptance hardening.
- UI surfaces: no UI polish or real provider work in this story.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Memory guard tests prove no direct `.fetchdf()` or `pd.read_csv`; fake LLM guardrail tests pass. |
| Integration | Demo-small and fake LLM run produce expected artifact sets. |
| E2E | Not applicable; no browser workflow change. |
| Platform | CLI/Make commands pass locally. |
| Release | Full pytest, Ruff, demo-small, fake LLM run, story verify, Harness audit, and trace pass before close. |

## Harness Delta

No harness behavior changes are expected.

## Evidence

- `.venv/bin/pytest -q` -> 31 passed.
- `.venv/bin/ruff check src tests` -> all checks passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> default demo passed with 15 issues.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4 --use-llm --llm-provider fake` -> fake LLM run passed, wrote `l4_report.md`.
- Structured artifact audit showed no missing deterministic files/charts in `outputs/demo_small`, no L4 artifacts in the default path, and all expected optional L4 artifacts in `outputs/demo_small_l4`.
- `outputs/demo_small_l4/guardrail_report.json` status is `passed`, with 3 checked numeric claims, 2 checked refs, and 0 violations.
- Guard scan found no production `pd.read_csv` or `pandas.read_csv`; direct `.fetchdf()` exists only in `duckdb_utils.fetch_bounded_df`.
- `scripts/bin/harness-cli story verify US-037` -> pass; 12 focused tests passed.
- Acceptance report written at `docs/releases/acceptance-2026-06-15.md`.

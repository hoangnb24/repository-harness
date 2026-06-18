# US-033 VSF Dataset Verdict Artifact

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler writes `dataset_verdict.json` alongside existing artifacts.
The artifact deterministically aggregates existing issue severities, schema
evaluation facts, and relationship graph status into a dataset-level readiness
verdict without adding LLM, charts, or renamed outputs.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- `dataset_verdict.json` includes `READY`, `WARN`, or `NOT_READY`, a 0-100 risk
  score, issue counts by severity and issue type, relationship status counts,
  schema summary inputs, top blockers, affected tables, and recommended next
  actions.
- Existing issue severities are normalized into a consistent P0-P3 aggregation
  model without changing the existing `issues.json` artifact shape.
- Markdown and HTML reports include a Dataset Verdict section and link the
  verdict artifact.
- Existing artifacts remain compatible: `profile_summary.json`, `issues.json`,
  `influence.json`, `schema_evaluation.json`, `relationship_graph.json`,
  `schema_diagram.json`, `schema_diagram.dbml`, runtime artifacts, reports, and
  `samples/`.
- The implementation does not add LLM, chart generation, artifact renames, or
  data repair behavior.

## Design Notes

- Commands: `vsf-profiler run`, `make demo-small`.
- Queries: verdict aggregation consumes already-produced issue, schema
  evaluation, and relationship graph artifacts.
- API: artifact builder lives under `src/vsf_profiler`.
- Tables: no product data model changes.
- Domain rules: severity normalization maps aliases into P0-P3; P0/P1 blockers
  or invalid schema/relationship facts make the verdict `NOT_READY`, lower
  severity findings make it `WARN`, and clean inputs make it `READY`.
- UI surfaces: static Markdown and HTML reports summarize the verdict.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Fixed issue/schema/graph fixtures prove severity aggregation, risk score, affected tables, and recommended actions. |
| Integration | Demo pipeline writes `dataset_verdict.json`, reports include Dataset Verdict, and runtime summary lists the artifact. |
| E2E | Not applicable; no browser workflow change. |
| Platform | CLI demo still writes existing artifacts plus the new verdict artifact. |
| Release | Full pytest, Ruff, and demo-small pass before close. |

## Harness Delta

No harness behavior changes are expected.

## Evidence

- Legacy tanlong severity/verdict references were read from
  `/Users/jin/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/ontology/models.py`,
  `src/severity/aggregator.py`, and `src/severity/compound.py`; only contract
  and deterministic aggregation ideas were reused.
- `.venv/bin/pytest -q tests/test_dataset_verdict.py tests/test_demo_small.py`
  -> `6 passed`.
- `.venv/bin/pytest -q` -> `22 passed`.
- `.venv/bin/ruff check src tests` -> passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> wrote
  `outputs/demo_small/report.html` and found 15 issues.
- `outputs/demo_small/dataset_verdict.json` records `NOT_READY`, risk score
  `100`, 15 total issues, severity counts `P0=2`, `P1=11`, `P2=0`, `P3=2`,
  relationship status `invalid=6`, top blockers, affected tables, and
  recommended next actions.
- `report.md` and `report.html` include the Dataset Verdict section and link
  `dataset_verdict.json`.
- `run_summary.json` includes `dataset_verdict` in `artifact_paths`.

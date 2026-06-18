# US-065 Visual Senior Data Scientist Generated Reports

## Status

implemented

## Lane

normal

## Product Contract

Generated `report.html`, `report.md`, package `index.html`, and package PDF
must present a clear Senior Data Scientist review from existing structured
artifacts rather than a sparse/raw artifact index.

The reports must preserve all artifact names and pipeline behavior while
showing:

- executive scorecard with verdict, risk, issues, blockers, table/row/column
  counts, FK health, and L4 status;
- inline chart visuals from existing `charts/*.json` specs;
- table impact and business-impact evidence from `table_assessments.json`;
- issue evidence with severity, table, columns, bad rows/rate, sample links,
  probable cause, and suggested fix;
- relationship, schema, and lineage summaries;
- guarded L4 narrative state when enabled and a clean deterministic no-LLM
  state otherwise.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Acceptance Criteria

- `report.html` and `report.md` use the Senior Data Scientist review layout.
- The export package index mirrors the same core evidence instead of a raw
  artifact dump.
- `analysis_report.pdf` is generated from the improved Markdown report.
- Optional L4 report and guardrail status are explicit when present.
- Default no-LLM runs remain deterministic and do not write L4 artifacts.
- No raw source CSV files or secrets are exposed in generated reports/packages.
- Olist `report.html` is understandable without opening raw JSON or Markdown.

## Design Notes

- Use existing artifacts only; no schema or artifact-name changes.
- Keep HTML visuals CSS-only and Markdown visuals text-only.
- Follow `.interface-design/system.md`: restrained data-quality console,
  system sans, flat surfaces, graphite/teal/amber/red signals, no cream/serif
  treatment.
- The package index is an offline review entrypoint; machine artifact links
  remain available but are no longer the primary narrative.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Focused report/L4/package tests. |
| Integration | Demo, fake-L4 smoke, package/PDF generation, artifact audit. |
| E2E | Browser screenshots for desktop/mobile report rendering. |
| Platform | Full pytest, Ruff, Node syntax, Playwright dashboard E2E, `make demo-full`. |
| Release | Harness story verification, audit, and trace. |

## Evidence

- `.venv/bin/pytest -q tests/test_demo_small.py tests/test_llm_narrative.py tests/test_export_package.py` -> 28 passed.
- `vsf-profiler run` no-LLM smoke wrote `outputs/demo_small_report_redesign/report.html`.
- `vsf-profiler run --use-llm --llm-provider fake` wrote `outputs/demo_small_l4_report_redesign/l4_report.md` and `guardrail_report.json` with status `passed`.
- `vsf-profiler package --zip --pdf` wrote `outputs/demo_small_report_redesign_package/index.html`, `analysis_report.pdf`, and zip.
- Olist smoke wrote `outputs/olist_report_redesign/report.html` with 9 tables, 1,550,922 rows, and review-score evidence.
- Screenshots captured:
  - `outputs/report_redesign_screenshots/desktop-report.png`
  - `outputs/report_redesign_screenshots/mobile-report.png`
  - `outputs/report_redesign_screenshots/olist-desktop-report.png`

## Harness Delta

No Harness policy changes were needed. The story adds evidence for generated
report presentation quality and package/PDF alignment.

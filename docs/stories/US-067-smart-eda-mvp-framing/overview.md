# Overview

## Current Behavior

VSF Data Profiler already profiles CSV folders against DBML/schema and writes
deterministic artifacts, but public docs, generated reports, package output,
web copy, and the L4 prompt overemphasize Senior Data Scientist, business
impact, table impact, dataset verdict, and release-candidate advanced surfaces.
That framing makes the product look like an enterprise/business platform rather
than a generic Smart EDA tool for data scientists.

## Target Behavior

The default product story is CSV folder plus DBML/schema plus optional rules
plus optional target column producing a Smart EDA/data-quality report. Existing
artifact names and JSON keys remain stable. Advanced surfaces such as
connectors, package/PDF export, lineage views, benchmarks, local dashboard, and
L4 provider usage are documented as optional or advanced.

## Affected Users

- Data scientists running local Smart EDA on relational CSV folders.
- Maintainers validating generated report, L4, package, and web copy.
- Reviewers reading README, product docs, and release/demo docs.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/demo/vsf-data-profiler.md`
- `docs/releases/v0.2-rc.md`

## Non-Goals

- No artifact renames.
- No removal of connector, package, dashboard, benchmark, PDF, or L4 code.
- No MySQL or PDF implementation changes.
- No new hosted backend behavior.

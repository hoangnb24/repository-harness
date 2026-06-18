# 0008 VSF Profiler Python CLI Stack

Date: 2026-06-15

## Status

Accepted

## Context

The supplied product spec asks for a local CLI that profiles CSV data against a
DBML contract, validates data quality, and emits report artifacts. The existing
repository is a generic Harness shell with no selected application stack.

## Decision

Use a Python package with a Typer CLI for VSF Data Profiler.

Core implementation choices:

- `typer` for the `vsf-profiler` command surface.
- `duckdb` for direct CSV querying and joins without full pandas loads.
- `pydantic` for normalized internal models.
- `pyyaml` for business rules.
- `jinja2` for deterministic Markdown and HTML reports.
- `pandas` only for bounded samples or in-memory analysis frames.
- Optional `scikit-learn` support for mutual information when installed.
- `pytest` for parser, rule, relationship, and end-to-end demo validation.

## Consequences

Positive:

- The MVP is locally runnable and does not require a service or database.
- DuckDB keeps profiling and relationship checks practical for larger CSVs.
- The CLI contract is easy to demo and test.

Tradeoffs:

- The DBML parser is pragmatic, not a complete grammar.
- Influence analysis reports association, not causation.
- Kaggle-backed Olist download remains dependent on user credentials.

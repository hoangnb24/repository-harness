# US-040 VSF Final Demo Package

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler has a concise v0.1 demo package that explains the default
demo, fake LLM demo, OpenAI smoke, artifact tour, guardrail caveats, and release
freeze summary without adding runtime features.

## Relevant Product Docs

- `README.md`
- `docs/demo/vsf-data-profiler.md`
- `docs/releases/v0.1.md`
- `docs/TEST_MATRIX.md`

## Acceptance Criteria

- Provide a 5-10 minute demo script.
- Provide commands for default demo, fake LLM, and OpenAI smoke.
- Include an artifact tour for `profile_summary.json`, `issues.json`,
  `schema_evaluation.json`, `relationship_graph.json`,
  `dataset_verdict.json`, `charts/*.json`, `l4_report.md`, and
  `guardrail_report.json`.
- Include the caveat that OpenAI may use deterministic fallback when guardrails
  reject provider output.
- Include a final v0.1 freeze summary.
- Do not change runtime code or add new features.

## Design Notes

- Commands: documentation only.
- Queries: none.
- API: none.
- Tables: none.
- Domain rules: no behavior changes.
- UI surfaces: no UI changes.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 0 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Not applicable for docs-only work. |
| Integration | Not applicable for docs-only work. |
| E2E | Not applicable; no browser workflow change. |
| Platform | `rg` checks prove required demo package sections and commands exist. |
| Release | `git diff --check`, story verify, and Harness audit pass. |

## Harness Delta

Added a durable story row for final demo documentation.

## Evidence

- `scripts/bin/harness-cli story verify US-040` -> pass.
- `git diff --check` -> pass.
- `rg` validation confirmed README, demo guide, release notes, and matrix
  contain the 5-10 minute demo script, command checklist, artifact tour,
  OpenAI fallback caveat, `guardrail_report.json`, and v0.1 freeze summary.

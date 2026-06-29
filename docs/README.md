# Documentation Map

This directory holds the project harness and any product contract derived from a
future user-provided spec.

## Main Files

- `HARNESS.md`: how humans and agents collaborate.
- `BRAINSTORM.md`: how exploratory ideas become selected intake-ready work.
- `FEATURE_INTAKE.md`: how prompts become tiny, normal, or high-risk work.
- `GIT_WORKFLOW.md`: how selected work moves through branch, proof, and merge.
- `VALIDATION_INTEGRITY.md`: anti-cheat controls for docs, proof, tests, CI,
  and traces.
- `ARCHITECTURE.md`: architecture discovery and boundary rules.
- `TEST_MATRIX.md`: legacy proof map; current proof status is queried with
  `scripts/bin/harness-cli query matrix`.
- `HARNESS_BACKLOG.md`: legacy improvement list; current improvement records
  are stored with `scripts/bin/harness-cli backlog`.
- `GLOSSARY.md`: shared terms.

## Folders

- `product/`: current product truth, empty until a spec is derived.
- `stories/`: feature packets and backlog.
- `decisions/`: durable decisions and tradeoffs.
- `demo/`: concrete walkthroughs that show how the harness transforms input
  into agent-ready work.
- `templates/`: reusable brainstorm, spec-intake, story, plan, decision, and
  validation formats.

## Current State

Harness v0 exists before implementation. These docs define how the project will
grow; they do not imply that app code, tests, CI, or deployment automation exist
yet.

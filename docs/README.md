# Documentation Map

This directory holds the project harness and any product contract derived from a
future user-provided spec.

## Main Files

- `HARNESS.md`: how humans and agents collaborate.
- `FEATURE_INTAKE.md`: how prompts become tiny, normal, or high-risk work.
- `ARCHITECTURE.md`: architecture discovery and boundary rules.
- `TEST_MATRIX.md`: legacy proof map; current proof status is queried with
  `scripts/bin/harness-cli query matrix`.
- `HARNESS_BACKLOG.md`: legacy improvement list; current improvement records
  are stored with `scripts/bin/harness-cli backlog`.
- `GLOSSARY.md`: shared terms.
- `contracts/`: versioned machine-readable contracts for optional external
  orchestrators.

## Folders

- `product/`: current product truth, empty until a spec is derived.
- `stories/`: feature packets and backlog.
- `decisions/`: durable decisions and tradeoffs.
- `demo/`: concrete walkthroughs that show how the harness transforms input
  into agent-ready work.
- `templates/`: reusable spec-intake, story, plan, decision, and validation
  formats.

## Current State

Harness v0 exists before implementation. These docs define how the project will
grow; they do not imply that app code, tests, CI, or deployment automation exist
yet.

# Documentation Map

Start with the smallest authoritative surface.

## Current Product

- `WORKFLOW.md`: repository understanding, missing capabilities, authority,
  and evidence.
- `ARCHITECTURE.md`: current product, code, state, update, and ownership
  boundaries.
- `HARNESS.md`: product principles and installed-core model.
- `product/`: current product behavior and installation contract.
- `decisions/`: lasting choices future work must inherit.
- `plans/`: optional locations for plans requested by the user or consumer workflow.
- [`patterns/encoding-invariants.md`](patterns/encoding-invariants.md): turn
  accepted architecture, reliability, security, and quality rules into native
  mechanical validation.
  It also covers fail-closed evidence gates and when to promote guidance to a
  gate.
- `research/`: exploratory notes, not product authority or release gates.
  `harness-gap-analysis.md` and `harness-requirements-ideas.md` (Vietnamese)
  compare this harness with the Learn Harness Engineering course.
- `templates/`: optional decision, plan, runbook, and Harness-improvement
  structures. The decision template carries checkable approval frontmatter.

## Consumer-Owned Truth

The consumer's README, product documents, architecture, code, tests, CI,
runtime signals, and application behavior remain authoritative. Harness does
not overwrite those with upstream product assumptions.

## Source Repository

- Root `README.md`: product overview, installation, maintenance, EOL, and
  development.
- `crates/harness/`: safe core installer/updater.
- `scripts/`: platform bootstrap, release, and validation entrypoints;
  `context-budget.tsv` holds the context size limits.
- `tests/`: behavior ownership and repository contract.

## History

The former SQLite control plane, protocol v1, story packets, migration evidence,
and compatibility documentation are preserved by Git history and immutable
`harness-cli-v*` tags. They are intentionally absent from the current tree so
search and agent retrieval return current product authority.

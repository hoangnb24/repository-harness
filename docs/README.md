# Documentation Map

Start with the smallest current map. Retrieve compatibility, historical, or
upstream-maintenance material only when the task explicitly needs it.

## Installed Core

- `WORKFLOW.md`: canonical request, planning, judgment, validation, and
  completion behavior.
- `product/`: consumer-owned product behavior derived from accepted intent.
- `plans/`: one evolving Git-native plan for work that needs durable memory.
- `decisions/`: lasting product and architecture choices.
- `templates/decision.md`: lasting-decision template.
- `templates/exec-plan.md`: durable execution-plan template.

These files are generic Harness structure. They do not select an application
stack, replace a consumer README or architecture, fabricate validation
commands, or require a CLI/database lifecycle.

## Consumer-Owned Truth

The consumer repository's own README, architecture, code, tests, CI, runtime
signals, and application behavior remain authoritative. Harness adds navigation
and working-memory structure around that truth; it does not install upstream
`repository-harness` product documents over it.

## Optional Source Indexes

The following material is deliberately outside the default installation:

- [Reduction Phase 3](https://github.com/hoangnb24/repository-harness/blob/main/PHASE3.md): current consumer-first application-legibility target, evidence matrix, and next gate.
- [Reduction Phase 4](https://github.com/hoangnb24/repository-harness/blob/main/PHASE4.md): completed SQLite control-plane freeze, compatibility boundary, and evidence gates.
- [Reduction Phase 5](https://github.com/hoangnb24/repository-harness/blob/main/PHASE5.md): completed optional-consumer ownership split between Harness, Symphony, and application evaluation.
- [CLI compatibility index](https://github.com/hoangnb24/repository-harness/blob/main/docs/compatibility/README.md): SQLite lifecycle, orchestration protocol, bootstrap, schemas, and CLI maintenance.
- [Historical index](https://github.com/hoangnb24/repository-harness/blob/main/docs/provenance/README.md): superseded decisions, story-era evidence, reviews, and migration provenance.
- [Upstream repository](https://github.com/hoangnb24/repository-harness): Rust implementation, installer, release, and maintenance truth.

Selecting the optional CLI profile installs the compatibility material required
to operate that surface. Historical and upstream-only material remains in the
source repository and Git history.

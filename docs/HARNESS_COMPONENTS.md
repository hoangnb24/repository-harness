# Harness Components

> **Compatibility reference — not the current default capability assessment.**
> This Phase 2 taxonomy records the historical control-plane design. Current
> investment is guided by repository and application legibility, mechanical
> invariants, observable proof, and reduced human attention.

This taxonomy maps the current `repository-harness` repository to two
component frameworks used by Phase 2 and updated by Phase 3 active
observability work:

- Runtime Substrate responsibilities: the 11 responsibility areas the harness
  should cover.
- NexAU decomposition: the seven implementation surfaces that influence agent
  behavior.

Status values:

- **Covered**: the repository has an explicit file, command, or record for this
  responsibility.
- **Partial**: the repository has some support, but the support is incomplete,
  manual, or not yet measured.
- **Missing**: no meaningful support exists yet.

## Responsibility Map

| # | Responsibility | Status | Harness Files | Evidence | Gap |
| --- | --- | --- | --- | --- | --- |
| 1 | Task specification | Covered | `AGENTS.md`, `docs/FEATURE_INTAKE.md`, `docs/templates/story.md`, `docs/templates/spec-intake.md`, `docs/templates/high-risk-story/*`, `docs/stories/*`, `intake` table, `story` table | Requests are classified by type and lane before implementation; normal and high-risk work have templates and durable story rows. | Keep story packets synchronized with future product docs. |
| 2 | Context selection | Covered | `AGENTS.md`, `docs/CONTEXT_RULES.md`, `docs/ARCHITECTURE.md`, `docs/decisions/*`, `docs/product/README.md`, `scripts/bin/harness-cli score-context` | Phase 2 adds phase-by-lane context rules and retrieval triggers; Phase 5 adds context scoring against recorded trace reads. | Future automation could enforce context selection instead of only measuring it. |
| 3 | Tool access | Covered | `scripts/bin/harness-cli`, `docs/TOOL_REGISTRY.md`, `tool` table, `crates/harness-cli/*`, `scripts/install-harness.sh`, `scripts/build-harness-cli-release.sh` | The Harness CLI exposes operational commands and a machine-readable tool manifest through `query tools`; external tools can be registered and removed. | Permission profiles and usage analytics remain future work. |
| 4 | Project memory | Covered | `docs/HARNESS.md`, `docs/decisions/*`, `docs/GLOSSARY.md`, `docs/HARNESS_BACKLOG.md`, `docs/stories/*`, `harness.db`, `decision`, `backlog`, and `trace` tables | Decisions, backlog, stories, and traces preserve durable knowledge across tasks. | Future work should add staleness checks and summarize old traces. |
| 5 | Task state | Covered | `scripts/bin/harness-cli query matrix`, `docs/TEST_MATRIX.md`, `intake` table, `story` table, `trace` table | Durable records track intake, story status, proof columns, and task traces. | Add lifecycle checks so in-progress stories cannot be forgotten. |
| 6 | Observability | Partial | `docs/TRACE_SPEC.md`, `trace` table, `scripts/bin/harness-cli trace`, `scripts/bin/harness-cli score-trace`, `scripts/bin/harness-cli query traces`, `scripts/bin/harness-cli query friction`, `docs/HARNESS_MATURITY.md` | Traces are auto-scored when recorded, can be rescored by command, and can be reviewed with friction context. | No dashboard or benchmark ingestion exists in this repo. |
| 7 | Failure attribution | Partial | `docs/HARNESS_COMPONENTS.md`, `docs/TRACE_SPEC.md`, `trace.errors`, `trace.harness_friction`, `docs/HARNESS_BACKLOG.md`, `backlog` table, `scripts/bin/harness-cli query friction` | Failures can be tied to files, components, friction, backlog proposals, and linked intake lane/type context. | No automated attribution from benchmark failures to harness components exists yet. |
| 8 | Verification | Covered | `docs/TEST_MATRIX.md`, `scripts/bin/harness-cli query matrix`, `scripts/bin/harness-cli story verify`, `scripts/bin/harness-cli story verify-all`, `scripts/bin/harness-cli trace`, `scripts/bin/harness-cli score-trace`, `story.verify_command`, `story.last_verified_result`, `.github/workflows/harness-cli-release.yml`, `docs/templates/validation-report.md` | Stories can store and run mechanical proof commands individually or in batch, traces warn when linked story verification has not passed, trace quality can be checked mechanically, and release workflow verifies Rust CLI releases. | Benchmark ingestion remains future work. |
| 9 | Permissions | Partial | `AGENTS.md`, `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, `docs/ARCHITECTURE.md`, installer conflict handling in `scripts/install-harness.sh` | Policy describes when agents may update docs and when to ask before architecture or workflow changes. | Permissions are instruction-level only; no enforced policy layer or command allowlist exists. |
| 10 | Entropy auditing | Covered | `docs/HARNESS_BACKLOG.md`, `docs/HARNESS_AUDIT.md`, `docs/IMPROVEMENT_PROTOCOL.md`, `backlog` table, `trace.harness_friction`, `scripts/bin/harness-cli audit`, `scripts/bin/harness-cli propose`, `docs/HARNESS_MATURITY.md` | Growth rule captures friction, audit detects drift and entropy score, backlog items compare predicted impact to actual outcome, and proposal generation can create reviewable backlog items. | Automated repair remains future work. |
| 11 | Intervention recording | Covered | `intervention` table, `scripts/bin/harness-cli intervention add`, `scripts/bin/harness-cli query interventions`, `trace` table, `docs/decisions/*`, `docs/stories/*`, `docs/HARNESS.md` | Human, reviewer, CI, and agent interventions are separate durable records and can be filtered by trace, story, or type. | Capture is still manual and advisory. |

## NexAU Cross-Reference

| Component | Harness Equivalent | Status | Notes |
| --- | --- | --- | --- |
| System prompts | `AGENTS.md` plus Harness policy docs | Covered | `AGENTS.md` is the stable shim; `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, and `docs/CONTEXT_RULES.md` carry evolving operating instructions. |
| Tool descriptions | `docs/TOOL_REGISTRY.md`, `scripts/README.md`, `docs/HARNESS.md`, `docs/TRACE_SPEC.md`, CLI help from `crates/harness-cli/src/interface.rs`, `scripts/bin/harness-cli query tools` | Covered | Commands are documented in a standalone registry and exposed as compiled plus registered tool manifest entries. |
| Tool implementations | `scripts/bin/harness-cli`, `crates/harness-cli/*`, `scripts/schema/001-init.sql`, `scripts/schema/002-story-verify.sql` | Covered | The Rust CLI is the primary durable-layer implementation and stable repo-local entrypoint. |
| Middleware | installer safety logic, feature intake workflow | Partial | The installer and intake process mediate work, but there is no runtime middleware enforcing policies. |
| Skills | `docs/templates/*`, `docs/FEATURE_INTAKE.md`, `docs/CONTEXT_RULES.md`, `docs/TRACE_SPEC.md` | Partial | Reusable procedures exist as markdown, not executable or installable agent skills. |
| Sub-agents | None in this repository | Missing | No delegated specialist agents or sub-agent protocols exist. |
| Long-term memory | `harness.db`, `docs/decisions/*`, `docs/stories/*`, `docs/HARNESS_BACKLOG.md`, `docs/GLOSSARY.md` | Covered | Durable records and markdown decisions preserve task history and project vocabulary. |

## File Inventory

Every tracked project file plus the Phase 2 input file is mapped to at least
one Runtime Substrate responsibility.

| File | Primary Responsibility | Secondary Responsibilities |
| --- | --- | --- |
| `.gitignore` | Tool access | Task state |
| `AGENTS.md` | Context selection | Task specification, permissions |
| `README.md` | Task specification | Project memory |
| `CONTRIBUTING.md` | Intervention recording | Project memory |
| `Cargo.toml` | Tool access | Verification |
| `Cargo.lock` | Tool access | Verification |
| `PHASE2.md` | Task specification | Observability, context selection |
| `PHASE3.md` | Task specification | Observability, verification, entropy auditing |
| `PHASE4.md` | Task specification | Verification, observability, task state |
| `PHASE5.md` | Task specification | Ownership and compatibility boundaries |
| `docs/compatibility/phase-5-evolution-infrastructure-legacy.md` | Historical task specification | Verification, entropy auditing, intervention recording |
| `crates/harness-cli/Cargo.toml` | Tool access | Verification |
| `crates/harness-cli/src/main.rs` | Tool access | Tool implementation |
| `crates/harness-cli/src/domain.rs` | Tool access | Task state, verification |
| `crates/harness-cli/src/application.rs` | Tool access | Task state |
| `crates/harness-cli/src/infrastructure.rs` | Tool access | Project memory, task state, observability |
| `crates/harness-cli/src/interface.rs` | Tool access | Context selection, verification |
| `docs/ARCHITECTURE.md` | Permissions | Context selection, task specification |
| `docs/FEATURE_INTAKE.md` | Task specification | Permissions, context selection |
| `docs/GLOSSARY.md` | Project memory | Context selection |
| `docs/HARNESS.md` | Task specification | Project memory, task state, permissions |
| `docs/HARNESS_BACKLOG.md` | Entropy auditing | Project memory, failure attribution |
| `docs/HARNESS_COMPONENTS.md` | Failure attribution | Observability, entropy auditing |
| `docs/HARNESS_MATURITY.md` | Entropy auditing | Observability, verification |
| `docs/HARNESS_AUDIT.md` | Entropy auditing | Verification, task state |
| `docs/IMPROVEMENT_PROTOCOL.md` | Entropy auditing | Failure attribution, permissions |
| `docs/CONTEXT_RULES.md` | Context selection | Permissions, task specification |
| `docs/TRACE_SPEC.md` | Observability | Failure attribution, intervention recording |
| `docs/TOOL_REGISTRY.md` | Tool access | Context selection, verification |
| `docs/README.md` | Project memory | Context selection |
| `docs/TEST_MATRIX.md` | Verification | Task state |
| `docs/decisions/0001-harness-first-development.md` | Project memory | Permissions |
| `docs/decisions/0002-post-spec-product-lifecycle.md` | Project memory | Task specification |
| `docs/decisions/0003-generic-spec-intake-harness.md` | Project memory | Task specification |
| `docs/decisions/0004-sqlite-durable-layer.md` | Project memory | Observability, task state |
| `docs/decisions/0005-prebuilt-rust-harness-cli.md` | Project memory | Tool access |
| `docs/decisions/0006-phase-4-benchmark-triage.md` | Project memory | Verification |
| `docs/decisions/0007-improvement-proposal-rules.md` | Project memory | Entropy auditing, permissions |
| `docs/decisions/README.md` | Project memory | Context selection |
| `docs/demo/README.md` | Task specification | Project memory |
| `docs/product/README.md` | Task specification | Project memory |
| `docs/review-fixes-1d30bf62-to-main.md` | Intervention recording | Failure attribution, verification |
| `docs/stories/README.md` | Task specification | Project memory |
| `docs/stories/US-001-install-harness.md` | Task specification | Verification, intervention recording |
| `docs/stories/US-008-trace-quality-scoring.md` | Task specification | Observability, verification |
| `docs/stories/US-009-enriched-friction-query.md` | Task specification | Failure attribution, observability |
| `docs/stories/US-011-backlog-outcome-workflow.md` | Task specification | Entropy auditing, project memory |
| `docs/stories/US-012-story-verify-command-field.md` | Task specification | Verification |
| `docs/stories/US-015-story-verify-command.md` | Task specification | Verification |
| `docs/stories/US-016-auto-trace-scoring-on-write.md` | Task specification | Observability, verification |
| `docs/stories/US-017-pre-close-verification-gate.md` | Task specification | Verification, permissions |
| `docs/stories/US-018-phase4-cli-ux-hardening.md` | Task specification | Tool access, verification |
| `docs/stories/US-019-machine-readable-tool-registry.md` | Task specification | Tool access |
| `docs/stories/US-020-batch-story-verification.md` | Task specification | Verification |
| `docs/stories/US-021-intervention-recording-schema.md` | Task specification | Intervention recording |
| `docs/stories/US-022-context-rule-measurement.md` | Task specification | Context selection |
| `docs/stories/US-023-drift-detection-entropy-score.md` | Task specification | Entropy auditing |
| `docs/stories/US-024-improvement-proposal-pipeline.md` | Task specification | Entropy auditing, permissions |
| `docs/stories/backlog.md` | Task specification | Project memory |
| `docs/stories/epics/README.md` | Task specification | Project memory |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/overview.md` | Task specification | Project memory |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/design.md` | Task specification | Tool access, permissions |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/execplan.md` | Task specification | Verification, task state |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/validation.md` | Verification | Intervention recording |
| `docs/stories/epics/E02-phase-2-observability-taxonomy/phase-2-progress.md` | Task state | Intervention recording |
| `docs/stories/epics/E03-phase-5-evolution-infrastructure/phase-5-progress.md` | Task state | Verification, entropy auditing |
| `docs/templates/decision.md` | Project memory | Task specification |
| `docs/templates/spec-intake.md` | Task specification | Context selection |
| `docs/templates/story.md` | Task specification | Verification |
| `docs/templates/validation-report.md` | Verification | Intervention recording |
| `docs/templates/high-risk-story/overview.md` | Task specification | Context selection |
| `docs/templates/high-risk-story/design.md` | Task specification | Permissions |
| `docs/templates/high-risk-story/execplan.md` | Task state | Verification |
| `docs/templates/high-risk-story/validation.md` | Verification | Failure attribution |
| `scripts/README.md` | Tool access | Context selection |
| `scripts/bin/harness-cli` | Tool access | Task state, observability |
| `scripts/bin/harness-cli` | Tool access | Task state, observability |
| `scripts/install-harness.sh` | Tool access | Permissions |
| `scripts/build-harness-cli-release.sh` | Verification | Tool access |
| `scripts/schema/001-init.sql` | Task state | Observability, project memory |
| `scripts/schema/002-story-verify.sql` | Verification | Task state, project memory |
| `scripts/schema/003-tool-registry.sql` | Tool access | Project memory |
| `scripts/schema/004-intervention.sql` | Intervention recording | Failure attribution |
| `.github/ISSUE_TEMPLATE/agent-failure-case.md` | Failure attribution | Entropy auditing |
| `.github/ISSUE_TEMPLATE/pattern-request.md` | Entropy auditing | Intervention recording |
| `.github/ISSUE_TEMPLATE/real-world-example.md` | Project memory | Intervention recording |
| `.github/workflows/harness-cli-release.yml` | Verification | Tool access |

## Coverage Summary

- Covered: 8/11 responsibilities.
- Partial: 3/11 responsibilities.
- Missing: 0/11 responsibilities.

Covered responsibilities:

- Task specification.
- Context selection.
- Tool access.
- Project memory.
- Task state.
- Verification.
- Entropy auditing.
- Intervention recording.
Partial responsibilities:

- Observability.
- Failure attribution.
- Permissions.

Phase 5 converts tool access, entropy auditing, and intervention recording into
covered responsibilities with a registry, drift audit, proposal loop, and
intervention schema. Later phases should focus on benchmark ingestion,
component-level attribution, permission enforcement, and tool usage analytics.

# Harness Components

This taxonomy maps the current `harness-experimental` repository to two
component frameworks used by Phase 2:

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
| 2 | Context selection | Covered | `AGENTS.md`, `docs/CONTEXT_RULES.md`, `docs/ARCHITECTURE.md`, `docs/decisions/*`, `docs/product/README.md` | Phase 2 adds phase-by-lane context rules and retrieval triggers while preserving the stable entry list in `AGENTS.md`. | Future automation could enforce context selection or measure over-reading. |
| 3 | Tool access | Partial | `scripts/harness`, `scripts/bin/harness-cli`, `scripts/README.md`, `crates/harness-cli/*`, `scripts/install-harness.sh`, `scripts/build-harness-cli-release.sh` | The Harness CLI exposes operational commands for intake, stories, decisions, backlog, traces, and queries. | No machine-readable tool registry, permission profile, or capability manifest exists yet. |
| 4 | Project memory | Covered | `docs/HARNESS.md`, `docs/decisions/*`, `docs/GLOSSARY.md`, `docs/HARNESS_BACKLOG.md`, `docs/stories/*`, `harness.db`, `decision`, `backlog`, and `trace` tables | Decisions, backlog, stories, and traces preserve durable knowledge across tasks. | Future work should add staleness checks and summarize old traces. |
| 5 | Task state | Covered | `scripts/harness query matrix`, `docs/TEST_MATRIX.md`, `intake` table, `story` table, `trace` table | Durable records track intake, story status, proof columns, and task traces. | Add lifecycle checks so in-progress stories cannot be forgotten. |
| 6 | Observability | Partial | `docs/TRACE_SPEC.md`, `trace` table, `scripts/harness query traces`, `scripts/harness query friction`, `docs/HARNESS_MATURITY.md` | Traces can be recorded and Phase 2 defines quality tiers and maturity targets. | No automated trace quality scoring, dashboard, or benchmark ingestion exists in this repo. |
| 7 | Failure attribution | Partial | `docs/HARNESS_COMPONENTS.md`, `docs/TRACE_SPEC.md`, `trace.errors`, `trace.harness_friction`, `docs/HARNESS_BACKLOG.md`, `backlog` table | Failures can be tied to files, components, friction, and backlog proposals. | No automated attribution from benchmark failures to harness components exists yet. |
| 8 | Verification | Partial | `docs/TEST_MATRIX.md`, `scripts/harness query matrix`, `story` proof columns, `.github/workflows/harness-cli-release.yml`, `docs/templates/validation-report.md` | Stories record unit, integration, E2E, and platform proof; release workflow verifies Rust CLI releases. | No generic verification runner, benchmark protocol file, or required final proof automation exists in this repo. |
| 9 | Permissions | Partial | `AGENTS.md`, `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, `docs/ARCHITECTURE.md`, installer conflict handling in `scripts/install-harness.sh` | Policy describes when agents may update docs and when to ask before architecture or workflow changes. | Permissions are instruction-level only; no enforced policy layer or command allowlist exists. |
| 10 | Entropy auditing | Partial | `docs/HARNESS_BACKLOG.md`, `backlog` table, `trace.harness_friction`, `docs/HARNESS_MATURITY.md` | Growth rule captures friction and Phase 2 defines maturity movement. | No drift detector, stale-doc audit, or entropy score exists. |
| 11 | Intervention recording | Partial | `trace` table, `docs/decisions/*`, `docs/stories/*`, `docs/HARNESS.md` | Traces and decisions can record actions, decisions, and outcomes. | Human interventions are not separated from normal agent actions, and there is no review-event schema. |

## NexAU Cross-Reference

| Component | Harness Equivalent | Status | Notes |
| --- | --- | --- | --- |
| System prompts | `AGENTS.md` plus Harness policy docs | Covered | `AGENTS.md` is the stable shim; `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, and `docs/CONTEXT_RULES.md` carry evolving operating instructions. |
| Tool descriptions | `scripts/README.md`, `docs/HARNESS.md`, CLI help from `crates/harness-cli/src/interface.rs` | Partial | Commands are documented, but there is no standalone tool schema or generated command reference. |
| Tool implementations | `scripts/harness`, `scripts/bin/harness-cli`, `crates/harness-cli/*`, `scripts/schema/001-init.sql` | Covered | The Rust CLI is the primary durable-layer implementation behind the stable repo-local entrypoint. |
| Middleware | `scripts/harness`, installer safety logic, feature intake workflow | Partial | The launcher and intake process mediate work, but there is no runtime middleware enforcing policies. |
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
| `docs/CONTEXT_RULES.md` | Context selection | Permissions, task specification |
| `docs/TRACE_SPEC.md` | Observability | Failure attribution, intervention recording |
| `docs/README.md` | Project memory | Context selection |
| `docs/TEST_MATRIX.md` | Verification | Task state |
| `docs/decisions/0001-harness-first-development.md` | Project memory | Permissions |
| `docs/decisions/0002-post-spec-product-lifecycle.md` | Project memory | Task specification |
| `docs/decisions/0003-generic-spec-intake-harness.md` | Project memory | Task specification |
| `docs/decisions/0004-sqlite-durable-layer.md` | Project memory | Observability, task state |
| `docs/decisions/0005-prebuilt-rust-harness-cli.md` | Project memory | Tool access |
| `docs/decisions/README.md` | Project memory | Context selection |
| `docs/demo/README.md` | Task specification | Project memory |
| `docs/product/README.md` | Task specification | Project memory |
| `docs/review-fixes-1d30bf62-to-main.md` | Intervention recording | Failure attribution, verification |
| `docs/stories/README.md` | Task specification | Project memory |
| `docs/stories/US-001-install-harness.md` | Task specification | Verification, intervention recording |
| `docs/stories/backlog.md` | Task specification | Project memory |
| `docs/stories/epics/README.md` | Task specification | Project memory |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/overview.md` | Task specification | Project memory |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/design.md` | Task specification | Tool access, permissions |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/execplan.md` | Task specification | Verification, task state |
| `docs/stories/epics/E01-durable-layer/US-002-rust-harness-cli/validation.md` | Verification | Intervention recording |
| `docs/stories/epics/E02-phase-2-observability-taxonomy/phase-2-progress.md` | Task state | Intervention recording |
| `docs/templates/decision.md` | Project memory | Task specification |
| `docs/templates/spec-intake.md` | Task specification | Context selection |
| `docs/templates/story.md` | Task specification | Verification |
| `docs/templates/validation-report.md` | Verification | Intervention recording |
| `docs/templates/high-risk-story/overview.md` | Task specification | Context selection |
| `docs/templates/high-risk-story/design.md` | Task specification | Permissions |
| `docs/templates/high-risk-story/execplan.md` | Task state | Verification |
| `docs/templates/high-risk-story/validation.md` | Verification | Failure attribution |
| `scripts/README.md` | Tool access | Context selection |
| `scripts/harness` | Tool access | Task state, observability |
| `scripts/bin/harness-cli` | Tool access | Task state, observability |
| `scripts/install-harness.sh` | Tool access | Permissions |
| `scripts/build-harness-cli-release.sh` | Verification | Tool access |
| `scripts/schema/001-init.sql` | Task state | Observability, project memory |
| `.github/ISSUE_TEMPLATE/agent-failure-case.md` | Failure attribution | Entropy auditing |
| `.github/ISSUE_TEMPLATE/pattern-request.md` | Entropy auditing | Intervention recording |
| `.github/ISSUE_TEMPLATE/real-world-example.md` | Project memory | Intervention recording |
| `.github/workflows/harness-cli-release.yml` | Verification | Tool access |

## Coverage Summary

- Covered: 4/11 responsibilities.
- Partial: 7/11 responsibilities.
- Missing: 0/11 responsibilities.

Covered responsibilities:

- Task specification.
- Context selection.
- Project memory.
- Task state.
Partial responsibilities:

- Tool access.
- Observability.
- Failure attribution.
- Verification.
- Permissions.
- Entropy auditing.
- Intervention recording.

The main Phase 2 improvement is that context selection becomes explicit and
observability gains a trace specification. Later phases should focus on
converting the partial areas into measurable checks.

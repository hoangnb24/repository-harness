# Changelog

## 2026-07-13 - PR #45

- feat(cutover): complete E11 repository separation (@hoangnb24)
- Merge commit: `2f613bcad6b01985165ccab65c87312142b30026`
- Harness CLI release: not required
- Changed files: 24 total (first 20 shown)
  - `docs/stories/epics/E11-symphony-repository-separation/README.md`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/design.md`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/README.md`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/canonical-target-ownership.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/canonical-target-ownership.json.sha256`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/cutover-readiness.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/proof/clean-install.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/proof/cleaned-contract.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/proof/cleaned-smoke.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/proof/initial-contract.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/proof/initial-smoke.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/proof/ownership-audit.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/proof/runtime-disposition.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/evidence/symphony-release.json`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/execplan.md`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/overview.md`
  - `docs/stories/epics/E11-symphony-repository-separation/US-100-cutover-and-post-separation-audit/validation.md`
  - `scripts/verify-e11-us100.sh`
  - `tests/core/assert-durable-state-boundary.sh`
  - `tests/cutover/assert-canonical-symphony-ownership.sh`
  - _… 4 additional file(s) omitted from this entry._

## 2026-07-12 - PR #44

- refactor(e11): complete Symphony repository separation (@hoangnb24)
- Merge commit: `22a6a06ad1cd89026b983108dc5ecae51ee7a655`
- Harness CLI release: `harness-cli-v0.1.15`
- Changed files: 465 total (first 20 shown)
  - `.agents/skills/impeccable/SKILL.md`
  - `.agents/skills/impeccable/agents/impeccable_asset_producer.toml`
  - `.agents/skills/impeccable/agents/impeccable_manual_edit_applier.toml`
  - `.agents/skills/impeccable/agents/openai.yaml`
  - `.agents/skills/impeccable/reference/adapt.md`
  - `.agents/skills/impeccable/reference/animate.md`
  - `.agents/skills/impeccable/reference/audit.md`
  - `.agents/skills/impeccable/reference/bolder.md`
  - `.agents/skills/impeccable/reference/brand.md`
  - `.agents/skills/impeccable/reference/clarify.md`
  - `.agents/skills/impeccable/reference/codex.md`
  - `.agents/skills/impeccable/reference/colorize.md`
  - `.agents/skills/impeccable/reference/craft.md`
  - `.agents/skills/impeccable/reference/critique.md`
  - `.agents/skills/impeccable/reference/delight.md`
  - `.agents/skills/impeccable/reference/distill.md`
  - `.agents/skills/impeccable/reference/document.md`
  - `.agents/skills/impeccable/reference/extract.md`
  - `.agents/skills/impeccable/reference/harden.md`
  - `.agents/skills/impeccable/reference/hooks.md`
  - _… 445 additional file(s) omitted from this entry._

## 2026-07-12 - PR #43

- Publish Harness orchestration protocol v1 and E11 separation foundations
  (@hoangnb24)
- Develop merge commit: `fa9fe27e2464ae9e60effcb7b8533f027b76a78b`
- Harness CLI release: `harness-cli-v0.1.14`
- The immutable `harness-cli-v0.1.12` tag did not publish a release: its
  verify job exposed and stopped on a child-exit/stdout-reader race in the
  retained Symphony adapter test. Version 0.1.13 drains final app-server
  output before classifying process exit.
- The immutable `harness-cli-v0.1.13` tag also remained unpublished: four
  native smokes passed, while Windows exposed an open-file rename violation in
  snapshot finalization. Version 0.1.14 closes the verified temporary database
  file before its atomic move and improves PowerShell failure diagnostics.
- Changed surfaces:
  - `crates/harness-cli/`
  - `scripts/schema/013-changeset-content-sha.sql`
  - `scripts/install-harness.sh`
  - `scripts/install-harness.ps1`
  - `.github/workflows/harness-cli-release.yml`
  - `docs/contracts/harness-orchestration-v1.md`
  - `docs/stories/epics/E11-symphony-repository-separation/`
  - `tests/protocol/`

## 2026-07-07 - PR #37

- US-070: completed (@hoangnb24)
- Merge commit: `ac748021b7a46b71ff7cde187f68073098b1a3b8`
- Harness CLI release: not required
- Changed files:
  - `.harness/changesets/run_1783405248236036000_24617_0.changeset.jsonl`
  - `crates/harness-symphony/web-ui/src/features/symphony/board.tsx`
  - `crates/harness-symphony/web-ui/tests/board.spec.ts`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-070-readable-done-column-task-cards.md`

## 2026-07-05 - PR #36

- US-068: completed (@hoangnb24)
- Merge commit: `5049c9704ca6f60f7446b9760603b2dcb4fecdf5`
- Harness CLI release: not required
- Changed files:
  - `.harness/changesets/run_1783224245101133000_18033_0.changeset.jsonl`
  - `crates/harness-symphony/web-ui/src/main.tsx`
  - `crates/harness-symphony/web-ui/src/styles.css`
  - `crates/harness-symphony/web-ui/tests/board.spec.ts`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-068-bounded-work-item-cards.md`

## 2026-07-04 - PR #35

- US-064: completed (@hoangnb24)
- Merge commit: `f7ace90df8d3ff16655dc29b42686d96a25f8fb3`
- Harness CLI release: not required
- Changed files:
  - `.harness/changesets/run_1783179886029971000_7111_0.changeset.jsonl`
  - `crates/harness-symphony/src/web.rs`
  - `crates/harness-symphony/src/work.rs`
  - `crates/harness-symphony/web-ui/src/main.tsx`
  - `crates/harness-symphony/web-ui/tests/board.spec.ts`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-064-ready-work-story-delete.md`

## 2026-07-04 - PR #34

- US-067: completed (@hoangnb24)
- Merge commit: `8c299574450c6febe91fa235c4642c7e4cb0afc4`
- Harness CLI release: not required
- Changed files:
  - `.harness/changesets/run_1783178537862657000_95182_0.changeset.jsonl`
  - `crates/harness-symphony/src/web.rs`
  - `crates/harness-symphony/web-ui/src/main.tsx`
  - `crates/harness-symphony/web-ui/tests/board.spec.ts`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-067-needs-attention-recovery-action.md`

## 2026-07-04 - PR #33

- US-066: completed (@hoangnb24)
- Merge commit: `fe26f2cde1d0e5e043dc807af35d945a975b51aa`
- Harness CLI release: not required
- Changed files:
  - `.harness/changesets/run_1783164291664744000_6614_2.changeset.jsonl`
  - `crates/harness-symphony/src/web.rs`
  - `crates/harness-symphony/web-ui/src/main.tsx`
  - `crates/harness-symphony/web-ui/tests/board.spec.ts`

## 2026-07-04 - PR #32

- US-065: completed (@hoangnb24)
- Merge commit: `67c1c64b1d479f6c04e509f363ae749017ce70a9`
- Harness CLI release: not required
- Changed files:
  - `.harness/changesets/run_1783163412740491000_6614_1.changeset.jsonl`
  - `crates/harness-symphony/src/agent.rs`
  - `crates/harness-symphony/src/interface.rs`
  - `docs/SYMPHONY_SCOPE.md`

## 2026-07-04 - PR #31

- Add Harness Symphony runner and Web UI controller (@hoangnb24)
- Merge commit: `61a642b9e496fd981c1ec9126b1695ec18463db3`
- Harness CLI release: `harness-cli-v0.1.11`
- Changed files:
  - `.gitignore`
  - `.harness/changesets/run_0000000000_seed_symphony_index.changeset.jsonl`
  - `.harness/changesets/run_1782473523_99206.changeset.jsonl`
  - `.harness/changesets/run_1782536604_52965.changeset.jsonl`
  - `.harness/changesets/run_1782543459_701.changeset.jsonl`
  - `.harness/changesets/run_1782550121_26667.changeset.jsonl`
  - `Cargo.lock`
  - `Cargo.toml`
  - `README.md`
  - `crates/harness-cli/Cargo.toml`
  - `crates/harness-cli/src/application.rs`
  - `crates/harness-cli/src/infrastructure.rs`
  - `crates/harness-cli/src/interface.rs`
  - `crates/harness-symphony/Cargo.toml`
  - `crates/harness-symphony/src/agent.rs`
  - `crates/harness-symphony/src/auto.rs`
  - `crates/harness-symphony/src/changeset.rs`
  - `crates/harness-symphony/src/config.rs`
  - `crates/harness-symphony/src/doctor.rs`
  - `crates/harness-symphony/src/interface.rs`
  - `crates/harness-symphony/src/main.rs`
  - `crates/harness-symphony/src/pr.rs`
  - `crates/harness-symphony/src/retention.rs`
  - `crates/harness-symphony/src/run.rs`
  - `crates/harness-symphony/src/state.rs`
  - `crates/harness-symphony/src/sync.rs`
  - `crates/harness-symphony/src/web.rs`
  - `crates/harness-symphony/src/work.rs`
  - `crates/harness-symphony/web-ui/electron/backend.cjs`
  - `crates/harness-symphony/web-ui/electron/browser-dev.cjs`
  - `crates/harness-symphony/web-ui/electron/dev.cjs`
  - `crates/harness-symphony/web-ui/electron/main.cjs`
  - `crates/harness-symphony/web-ui/electron/smoke.cjs`
  - `crates/harness-symphony/web-ui/index.html`
  - `crates/harness-symphony/web-ui/package-lock.json`
  - `crates/harness-symphony/web-ui/package.json`
  - `crates/harness-symphony/web-ui/playwright.config.ts`
  - `crates/harness-symphony/web-ui/postcss.config.js`
  - `crates/harness-symphony/web-ui/src/components/ui/badge.tsx`
  - `crates/harness-symphony/web-ui/src/components/ui/button.tsx`
  - `crates/harness-symphony/web-ui/src/components/ui/card.tsx`
  - `crates/harness-symphony/web-ui/src/components/ui/input.tsx`
  - `crates/harness-symphony/web-ui/src/components/ui/separator.tsx`
  - `crates/harness-symphony/web-ui/src/lib/utils.ts`
  - `crates/harness-symphony/web-ui/src/main.tsx`
  - `crates/harness-symphony/web-ui/src/run-log.ts`
  - `crates/harness-symphony/web-ui/src/styles.css`
  - `crates/harness-symphony/web-ui/tailwind.config.ts`
  - `crates/harness-symphony/web-ui/tests/board.spec.ts`
  - `crates/harness-symphony/web-ui/tsconfig.json`
  - `crates/harness-symphony/web-ui/vite.config.ts`
  - `docs/README.md`
  - `docs/SYMPHONY_QUICKSTART.md`
  - `docs/SYMPHONY_SCOPE.md`
  - `docs/TOOL_REGISTRY.md`
  - `docs/design/symphony-web-ui-controller/README.md`
  - `docs/design/symphony-web-ui-controller/artifact.json`
  - `docs/design/symphony-web-ui-controller/critique.json`
  - `docs/design/symphony-web-ui-controller/data.json`
  - `docs/design/symphony-web-ui-controller/mqum833g-drawing-2026-06-26T07-34-24-936Z.png`
  - `docs/design/symphony-web-ui-controller/provenance.json`
  - `docs/design/symphony-web-ui-controller/template.html`
  - `docs/design/symphony-web-ui-controller/template.html.artifact.json`
  - `docs/product/README.md`
  - `docs/product/symphony-web-ui-controller.md`
  - `docs/reviews/develop-to-main-pr-review.md`
  - `docs/stories/US-001-install-harness.md`
  - `docs/stories/US-046-first-class-symphony-codex-adapter.md`
  - `docs/stories/epics/E04-symphony-cli-prerequisites/README.md`
  - `docs/stories/epics/E04-symphony-cli-prerequisites/US-028-harness-db-path.md`
  - `docs/stories/epics/E04-symphony-cli-prerequisites/US-029-operation-log-writing.md`
  - `docs/stories/epics/E04-symphony-cli-prerequisites/US-030-changeset-apply.md`
  - `docs/stories/epics/E04-symphony-cli-prerequisites/US-031-db-rebuild.md`
  - `docs/stories/epics/E05-symphony-local-runner/README.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-032-symphony-crate-config.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-033-symphony-doctor.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-034-work-list.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-035-run-state-lock.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-036-prepare-isolated-run.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-037-run-contract-agents-shim.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-038-result-validation-agent-adapter.md`
  - `docs/stories/epics/E05-symphony-local-runner/US-039-runs-status.md`
  - `docs/stories/epics/E06-symphony-review-sync/README.md`
  - `docs/stories/epics/E06-symphony-review-sync/US-040-changeset-rendering.md`
  - `docs/stories/epics/E06-symphony-review-sync/US-041-optional-pr-creation.md`
  - `docs/stories/epics/E06-symphony-review-sync/US-042-symphony-sync.md`
  - `docs/stories/epics/E06-symphony-review-sync/US-043-artifact-retention.md`
  - `docs/stories/epics/E07-symphony-automation/README.md`
  - `docs/stories/epics/E07-symphony-automation/US-044-tiny-here-run.md`
  - `docs/stories/epics/E07-symphony-automation/US-045-auto-mode-work-sources.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/README.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-047-dependency-board-foundation.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-047-dependency-board-foundation/design.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-047-dependency-board-foundation/execplan.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-047-dependency-board-foundation/overview.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-047-dependency-board-foundation/validation.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-048-local-web-backend-api.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-049-browser-board-task-detail-ui.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-050-run-start-event-api.md`
  - `docs/stories/epics/E08-symphony-web-ui-controller/US-051-review-surface-run-artifacts.md`

## 2026-06-15 - PR #20

- fix: add missing files to installer file lists (@NguyenQS504092s)
- Merge commit: `e3a83390be59eafcf361afe61672db1a9ed0a440`
- Harness CLI release: not required
- Changed files:
  - `scripts/install-harness.ps1`
  - `scripts/install-harness.sh`

## 2026-06-13 - PR #19

- feat(cli): kind-aware inbound tool registry with presence scanning (@thanh-dong)
- Merge commit: `04177b25a7f7e1c5acd24b71127db331c1b6602c`
- Harness CLI release: `harness-cli-v0.1.10`
- Changed files:
  - `AGENTS.md`
  - `README.md`
  - `crates/harness-cli/src/application.rs`
  - `crates/harness-cli/src/domain.rs`
  - `crates/harness-cli/src/infrastructure.rs`
  - `crates/harness-cli/src/interface.rs`
  - `docs/TOOL_REGISTRY.md`
  - `docs/stories/US-027-inbound-tool-registry.md`
  - `scripts/install-harness.sh`
  - `scripts/schema/005-tool-extensions.sql`

## 2026-06-09 - PR #13

- docs(phase5): Phase 5 — Evolution Infrastructure scope (@hoangnb24)
- Merge commit: `bfef94a77acfa33af81f6da96bc06f053d7f5164`
- Harness CLI release: `harness-cli-v0.1.9`
- Changed files:
  - `PHASE5.md`
  - `crates/harness-cli/src/application.rs`
  - `crates/harness-cli/src/domain.rs`
  - `crates/harness-cli/src/infrastructure.rs`
  - `crates/harness-cli/src/interface.rs`
  - `docs/FEATURE_INTAKE.md`
  - `docs/GLOSSARY.md`
  - `docs/HARNESS.md`
  - `docs/HARNESS_AUDIT.md`
  - `docs/HARNESS_COMPONENTS.md`
  - `docs/HARNESS_MATURITY.md`
  - `docs/IMPROVEMENT_PROTOCOL.md`
  - `docs/TOOL_REGISTRY.md`
  - `docs/decisions/0007-improvement-proposal-rules.md`
  - `docs/stories/US-019-machine-readable-tool-registry.md`
  - `docs/stories/US-020-batch-story-verification.md`
  - `docs/stories/US-021-intervention-recording-schema.md`
  - `docs/stories/US-022-context-rule-measurement.md`
  - `docs/stories/US-023-drift-detection-entropy-score.md`
  - `docs/stories/US-024-improvement-proposal-pipeline.md`
  - `docs/stories/epics/E03-phase-5-evolution-infrastructure/phase-5-progress.md`
  - `scripts/install-harness.sh`
  - `scripts/schema/003-tool-registry.sql`
  - `scripts/schema/004-intervention.sql`

## 2026-06-09 - Post-Merge Automation

- Added post-merge changelog automation for merged pull requests.
- Added conditional Harness CLI patch release automation when merged PRs change Rust CLI source, schema, Cargo metadata, or release packaging files.
- Reused the existing Harness CLI release workflow for release builds so tag, manual, and post-merge releases share the same verification and asset publishing path.

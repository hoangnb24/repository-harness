# 0014 Distill Upstream Observability Concepts (markdown-first, no compiled tooling)

Date: 2026-06-01

## Status

Accepted

## Context

This fork (`huunghiaish/harness-experimental`) diverged from upstream
(`hoangnb24/harness-experimental`) after a shared harness-v0 ancestor. Upstream
evolved toward a **measurable-harness product**: a Rust CLI (~3,600 LOC), a
SQLite durable layer, trace auto-scoring, a maturity ladder benchmarked against
an external `harness-benchmark`, story-verify gates, Windows installer, and CI
releases (v0.1.3 → v0.1.7). This fork evolved toward a **solo-dev / agency
delivery harness**: a 13-stage WORKFLOW, self-review lane, stage-runner
subagent, bilingual VN/EN client-delivery templates, Telegram + context-monitor
hooks — markdown-first, no compiled runtime.

An evaluation of upstream's upgrades (report:
`plans/reports/eval-260601-upstream-harness-distillation.md`) found most of
upstream's work serves the "harness as product" goal and is not needed here
(Rust CLI, SQLite, Windows installer, CI release, community infra). But five
**concepts** were judged cheap-to-port and genuinely useful for this fork's
goal, if re-expressed markdown-first.

User decision (2026-06-01): fork stays **internal, not packaged as a product**.
Port the three high-value concepts plus distill two reference docs — without
pulling any Rust/SQLite/CI machinery.

## Decision

Adopt five upstream concepts, all re-authored markdown-first and re-grounded in
this fork's 13-stage + self-review model. No code, no database, no binary.

1. **Maturity ladder** → `docs/HARNESS_MATURITY.md`. Levels verifiable by repo
   state (stages wired, gates present, trace discipline), not by an external
   benchmark. Self-positions the fork at **H3 entering H4**.

2. **Component taxonomy** → `docs/HARNESS_COMPONENTS.md`. Maps local harness
   surfaces to the generic 11-responsibility framework (Runtime Substrate
   arXiv 2605.13357). Coverage: 6 Covered / 5 Partial / 0 Missing. The five
   Partials are the deliberate "instruction-level not enforced" shape.

3. **Mechanical verification gate** → `docs/TEST_MATRIX.md` § Verification
   Register (Verify command + Last verified + Result) + `docs/FEATURE_INTAKE.md`
   § Pre-Close Verification Gate + `AGENTS.md` Done Definition bullet. A story
   cannot close until its Verify command ran `pass`, or a recorded reason
   explains why none exists. Enforced by **instruction**, not a commit hook.

4. **Context engineering rules** → `docs/CONTEXT_RULES.md`. What to read per
   stage-group and lane; pairs with `.claude/hooks/context-monitor.sh` (the
   hook says how much budget is spent; the doc says what to spend it on).

5. **Trace spec + self-scoring** → `docs/TRACE_SPEC.md`. A markdown trace block
   (not a SQLite row) with three tiers (minimal/standard/detailed) the agent
   self-scores against the lane. Trace lands in the session retrospective;
   the Friction field feeds the Growth Rule → `HARNESS_BACKLOG.md`. Wired into
   `docs/playbooks/session-retrospective.md` (new § Trace) and `docs/HARNESS.md`
   § Growth Rule.

## What This Decision Deliberately Excludes

Rejected from upstream as off-goal for an internal delivery harness:

- **Rust CLI + SQLite durable layer** — the file tree + git history is the
  durable store at solo scale. A compiled tool adds a build dependency that
  violates the Independence Principle (`docs/HARNESS.md`).
- **Trace auto-scoring binary** — self-scoring is the markdown stand-in.
- **Windows PowerShell installer, CI release workflow, versioned binaries** —
  only meaningful when shipping the harness as a distributable product.
- **Community infra** (CONTRIBUTING, issue templates, growth README) — only for
  open-source contributor funnels.

If the fork's goal ever changes from "deliver client projects" to "publish a
measurable harness," re-open these — that is the boundary, and it is explicit.

## Drift / Confirmation Trail

- The verification gate is **instruction-enforced** by design — a user
  constraint (internal use, markdown-first), not an oversight. Hard enforcement
  (commit hook / binary) is a documented future option, not a gap.
- No existing user decision was reversed. The self-review lane (`0013`), stage
  boundary commits (`0012`), and Independence Principle are all preserved and
  the new docs cite them rather than overriding.
- All five docs label their upstream origin and the markdown-first adaptation so
  a future reader can trace what was borrowed vs invented.

## Alternatives Considered

1. **Merge `upstream/main` wholesale.** Rejected: histories diverged deeply;
   pulls Rust/SQLite/CI that contradict the markdown-first goal and would cause
   large conflicts. The `merge/upstream-eval` branch is for selective
   distillation, not a branch merge.
2. **Port nothing; stay as-is.** Rejected: the five concepts close real gaps
   (no context-reading guide, no mechanical verify gate, no trace tiering) at
   near-zero cost since they are pure docs.
3. **Port the verify gate as a real commit hook now.** Rejected (deferred):
   over-engineering for solo use; instruction-level + human review is enough
   until a second person or a CI need appears.

## Files Added / Changed

- Added: `docs/HARNESS_MATURITY.md`, `docs/HARNESS_COMPONENTS.md`,
  `docs/CONTEXT_RULES.md`, `docs/TRACE_SPEC.md`.
- Changed: `docs/TEST_MATRIX.md` (§ Verification Register),
  `docs/FEATURE_INTAKE.md` (§ Pre-Close Verification Gate),
  `AGENTS.md` (Source Of Truth pointers + Done Definition),
  `docs/HARNESS.md` (§ Growth Rule → trace link),
  `docs/playbooks/session-retrospective.md` (§ Trace),
  `AGENTS.md` (§ Verify Gate — No Bypass),
  `scripts/install-harness.sh` (HARNESS_FILES list + `core.hooksPath`
  activation — the 4 new docs, this decision, and the verify-gate hooks now
  propagate to bootstrapped projects).
- Added (hook): `scripts/hooks/harness-verify-gate.sh`, `.githooks/pre-commit`,
  `.githooks/pre-push`.

## Hard Enforcement: Adopted (Option C)

Initially this gate was proposed as instruction-only, with a hard git hook
deferred as off-goal for solo use. **Reversed 2026-06-01 — user supplied new
data that changes the threat model**, so the deferral no longer holds:

1. The project is now a **2-person team**, not solo — the "human already
   reviews every gate themselves" assumption is gone.
2. Work runs as **autonomous `/goal` sessions** where the human does not watch
   each commit, so the verify gate is easy to miss in practice.
3. Recurring real failures: **agents report "done" when work is not actually
   done**, and **lint errors get committed/pushed** anyway.

These are exactly the conditions named for re-opening C. Decision: ship a
**hard, blocking** git hook (Option C).

Implementation:
- `scripts/hooks/harness-verify-gate.sh` — shared core. Gate 1: auto-detected
  lint/validate (npm/pnpm/yarn script, Makefile target, or `cargo clippy`),
  blocks on failure. Gate 2: parses `docs/TEST_MATRIX.md` § Verification
  Register, blocks any `Result: fail`; on a stage-close commit (STAGE.md staged)
  also blocks `Result: never-run`.
- `.githooks/pre-commit` + `.githooks/pre-push` — thin wrappers; pre-push is the
  backstop before sharing.
- `scripts/install-harness.sh` activates it via `git config core.hooksPath
  .githooks` (existing-repo installs and bootstrap after `git init`).
- `AGENTS.md` § Verify Gate — No Bypass: agents must not use `--no-verify`/`-n`
  or unset `core.hooksPath`; `--no-verify` is a human-only override with a
  stated reason.

False-positive guard (the original fragility worry): the parser skips the `TBD`
placeholder/header/separator rows; `fail` blocks always (unambiguous), but
`never-run` blocks **only at stage-close**, so normal WIP commits of
not-yet-verified stories are not blocked. Verified by `pre-commit`/`pre-push`
integration tests across clean / fail / never-run / stage-close cases.

Residual limit: `git --no-verify` skips client-side hooks entirely, so the
no-bypass guarantee for **agents** is the `AGENTS.md` instruction, not the hook.
A true server-side backstop (CI check / pre-receive) is the next step if humans
also bypass; deferred until that is observed.

# Upstream Harness Evaluation + Distillation

**Date:** 2026-06-01 · **Branch:** merge/upstream-eval · **Type:** eval + port

Upstream: `https://github.com/hoangnb24/harness-experimental` (remote `upstream`).
Fork: `huunghiaish/harness-experimental` (remote `origin`).

## TL;DR

Two repos diverged from a shared harness-v0 ancestor into **different goals** —
not a version bump. Upstream = "harness as measurable product" (Rust CLI +
SQLite + benchmark + releases). Fork = "solo-dev/agency delivery harness"
(13-stage WORKFLOW + self-review + VN templates + hooks, markdown-first).

User confirmed fork stays **internal, not packaged**. Distilled **5 upstream
concepts** into markdown-first form; rejected all compiled/product machinery.
Decision: `docs/decisions/0014-distill-upstream-observability-concepts.md`.

## Divergence Map

| Axis | Fork (origin) | Upstream (hoangnb24) |
| --- | --- | --- |
| Goal | Internal client delivery | Measurable harness product |
| Durable store | File tree + git + STAGE.md | Rust CLI + SQLite `harness.db` |
| Signature work | 13 stages, self-review lane, stage-runner, VN/EN delivery templates, Telegram/context hooks | Trace auto-scoring, maturity ladder vs `harness-benchmark`, story-verify CLI, 4 phases, releases v0.1.3→v0.1.7 |
| Grounding | Vibecode delivery experience | 5–9 arXiv papers |

Upstream is ~50 commits ahead on its track; fork ~60 commits ahead on its own.
Wholesale merge rejected — deep divergence, would pull Rust/SQLite/CI.

## Usefulness Ratings (for THIS fork's internal goal, /10)

| Upstream upgrade | Score | Verdict |
| --- | --- | --- |
| Maturity ladder (H0–H4) | 6 | **Ported** (adapted, repo-state-verifiable) |
| Component taxonomy (11 responsibilities) | 6 | **Ported** (coverage audit) |
| Mechanical verify gate (story verify + pre-close) | 6 | **Ported** (instruction-level, no binary) |
| CONTEXT_RULES (read-by-phase × lane) | 5→6 | **Ported** (pairs with context-monitor hook) |
| TRACE_SPEC + scoring | 4→6 | **Ported** (markdown trace + self-score) |
| Rust CLI durable layer (~3.6k LOC) | 3 | Rejected — build dep vs Independence Principle |
| SQLite `harness.db` | 3 | Rejected — file tree is the store at solo scale |
| Windows PowerShell installer | 2 | Rejected — Linux/solo |
| CI release + versioned binary | 2 | Rejected — not a product |
| Community infra (CONTRIBUTING/issues/growth README) | 2 | Rejected — no contributor funnel |

"Pull everything" ≈ 3.5/10. "Distill the doc-level concepts" ≈ 6/10 — done.

## What Was Ported (markdown-first, adapted)

1. `docs/HARNESS_MATURITY.md` — ladder by verifiable repo state. Fork = **H3
   entering H4**.
2. `docs/HARNESS_COMPONENTS.md` — 11-responsibility coverage audit (6 Covered /
   5 Partial / 0 Missing). Partials = deliberate instruction-level shape.
3. **Verify gate** — `docs/TEST_MATRIX.md` § Verification Register (Verify cmd +
   Last verified + Result) + `docs/FEATURE_INTAKE.md` § Pre-Close Verification
   Gate + `AGENTS.md` Done Definition bullet.
4. `docs/CONTEXT_RULES.md` — read-lists per stage-group × lane + retrieval
   triggers + token budget; pairs with `context-monitor.sh`.
5. `docs/TRACE_SPEC.md` — tiered markdown trace + self-scoring; wired into
   `session-retrospective.md` (§ Trace) and `HARNESS.md` Growth Rule.

## What Was Rejected And Why

Rust CLI, SQLite, trace-scoring binary, Windows installer, CI release, community
infra — all serve the "harness as product" path. Boundary is explicit in `0014`:
re-open only if the goal changes from "deliver client projects" to "publish a
measurable harness."

## Adaptation Choices

- Upstream lanes (tiny/normal/high-risk) → mapped onto fork's **self-review**
  default (follows Normal column unless a risk flag escalates).
- Upstream CLI references (`harness-cli query matrix`, `score-trace`) → replaced
  with markdown sources (TEST_MATRIX, self-score rubric).
- Upstream's 4 context phases → collapsed onto the fork's **13 stages** as five
  stage-groups.
- Upstream trace = SQLite row → fork trace = markdown block in the retro report.

## Verification

- Pre-Close Verification Gate for this very change: no automated suite in the
  harness repo (docs-only). Verify = `rg` cross-reference check that every new
  doc is linked from `AGENTS.md` + cited by `0014`. Result: pass (manual).
- Trace tier: this is a harness-improvement (normal lane) → Standard trace below.

### Trace — distilled 5 upstream concepts into markdown-first harness docs

- **Outcome:** completed
- **Stage / Lane:** harness self-development (meta) / self-review→normal
- **Story / tokens:** n/a (harness improvement, no US-)
- **Files read:** upstream/main `HARNESS_MATURITY.md`, `HARNESS_COMPONENTS.md`,
  `CONTEXT_RULES.md`, `TRACE_SPEC.md`, `PHASE2/3/4.md`, interface.rs; local
  `AGENTS.md`, `HARNESS.md`, `WORKFLOW.md`, `FEATURE_INTAKE.md`, `TEST_MATRIX.md`,
  `STAGE.md`, `0013`, `session-retrospective.md`
- **Files changed:** 4 added (MATURITY, COMPONENTS, CONTEXT_RULES, TRACE_SPEC),
  1 decision (0014), 1 report; edited TEST_MATRIX, FEATURE_INTAKE, AGENTS,
  HARNESS, session-retrospective
- **Decisions:** markdown-first only; reject Rust/SQLite/CI; verify gate stays
  instruction-level; one consolidated decision (0014) not five
- **Verify:** `rg` link-coverage check across new docs — pass
- **Friction:** none — local harness conventions (lanes, tokens, decision
  format, STAGE.md) mapped cleanly onto upstream concepts

## Unresolved Questions

1. ~~Hard enforcement?~~ **Resolved 2026-06-01: Option C chosen** (new data —
   2-person team, autonomous goals, recurring lint-leak + done-but-not-done).
   Shipped a blocking `pre-commit`/`pre-push` hook (`scripts/hooks/
   harness-verify-gate.sh`) + agent no-bypass rule. See `0014` § Hard
   Enforcement. Residual: `git --no-verify` skips client-side hooks → a CI /
   server-side backstop is the next step if humans also bypass.
2. ~~Propagate to bootstrapped projects?~~ **Resolved 2026-06-01:** the 4 new
   docs + decision 0014 + verify-gate hooks added to `scripts/install-harness.sh`
   (HARNESS_FILES + `core.hooksPath` activation).
3. **Merge target.** Work is on `merge/upstream-eval`. Merge to `main`, open a
   PR, or leave on the branch for review first?

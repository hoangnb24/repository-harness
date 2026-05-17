# Build Execution

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Stage-8 build discipline. What an agent (or solo dev) actually does between "story is sliced" and "code is up for review." Composes with `docs/templates/story.md § Implementation Guardrails` — guardrails state the rules; this playbook says how to enforce them.

## When To Run

- Starting any story implementation work (stage 8 of `solo-dev-client-delivery.md`).
- Setting up a fresh project after the stack-selection decision lands.
- Onboarding a new collaborator onto an in-flight project.

Skip when: the task is a doc-only change with no code touched.

## Branching Strategy

Solo dev / small team default: **trunk-based** on `main`.

- Direct commits to `main` are fine for tiny-lane work (docs, narrow edits, low-risk fixes).
- Normal + high-risk stories: short-lived feature branch per story, merged to `main` via PR after stage 9 code review.
  - Branch name: `feat/US-NNN-short-slug` or `fix/US-NNN-short-slug`.
  - Lifetime ≤ 2 days. If a story spans longer, split it.
- Long-lived branches (`dev`, `staging`, `release/*`) only when CI/CD targets them. Solo dev rarely needs more than `main`.

Variants for multi-collaborator projects: trunk-based still preferred; use Pull Requests as the review surface even when working solo (creates an audit trail at stage 9).

## Commit Cadence

Commit on a clean, runnable state. Roughly:

- Every 30-90 minutes of focused work.
- Always before stopping for the day.
- Always before switching stories.
- Never on a broken-test state without an explicit `WIP:` prefix + same-day fix commit.

The 6-dim review rubric at stage 9 (`code-review-scoring.md`) penalises massive commits that hide review-blockers. Smaller commits = higher scores.

## Commit Message Format

Conventional commits. Body MUST cite at least one composite token (`US-NNN.REQ-MMM`, `US-NNN.SC-MMM`, or `US-NNN.TC-MMM`) per `docs/HARNESS.md § Traceability Tokens`.

```text
<type>(<scope>): <subject under 70 chars>

<paragraph explaining WHY, not WHAT — diff shows WHAT>

Cites: US-014.REQ-002, US-014.SC-007
```

Types (conventional): `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`, `build`, `ci`.

### Token-Citation Hook (Recommended)

Drop the following into `.git/hooks/commit-msg` (chmod +x):

```bash
#!/usr/bin/env bash
msg_file="$1"
# Allow merge / revert / fixup commits without token requirement.
first_line="$(head -1 "$msg_file")"
case "$first_line" in
  "Merge "* | "Revert "* | "fixup! "* | "squash! "* | "WIP:"*) exit 0 ;;
esac
# Require US-NNN.{REQ|SC|TC}-MMM somewhere in the body (or Cites: line).
if ! grep -qE 'US-[0-9]+\.(REQ|SC|TC)-[0-9]+' "$msg_file"; then
  echo "commit-msg: missing US-NNN.{REQ|SC|TC}-MMM token. Cite at least one." >&2
  exit 1
fi
```

Tiny-lane work is exempt (no token required per `docs/HARNESS.md § Traceability Tokens`); use the `WIP:` prefix or a custom `chore:` subject to bypass.

## Pre-Commit Hook Recipe

Goal: catch lint / format / typecheck issues before the commit lands. Recipe varies by stack (per `docs/templates/code-standards.md` § Tooling).

### Node / TypeScript example

Install [husky](https://typicode.github.io/husky/) + [lint-staged](https://github.com/lint-staged/lint-staged):

```bash
pnpm add -D husky lint-staged
pnpm dlx husky init
```

`.husky/pre-commit`:

```bash
pnpm exec lint-staged
```

`package.json`:

```json
{
  "lint-staged": {
    "*.{ts,tsx,js,jsx}": ["eslint --fix", "prettier --write"],
    "*.{md,json,yml,yaml}": ["prettier --write"]
  }
}
```

### Python example

Use [pre-commit](https://pre-commit.com/) framework. `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
```

Then: `pre-commit install`.

### Go example

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
set -e
gofmt -l -s . | grep . && { echo "gofmt failed"; exit 1; } || true
go vet ./...
golangci-lint run
```

## Secrets & `.env` Policy

- `.env` is **never** committed. `.env.example` IS committed and lists every required variable with empty value + one-line purpose.
- `.gitignore` MUST contain `.env`, `.env.*`, but NOT `.env.example`.
- Local dev: real values live in `.env` (gitignored). Production values live in the secret vault chosen in stack-selection decision.
- Pre-commit safeguard: extend the recipe above with a secret-scan step.

### Secret-Scan Hook (Recommended)

Append to the pre-commit hook:

```bash
# Block accidental commits of .env (not .env.example)
if git diff --cached --name-only | grep -E '^\.env(\..*)?$' | grep -v '^\.env\.example$' >/dev/null; then
  echo "pre-commit: refusing to commit .env file — use .env.example for shape only" >&2
  exit 1
fi
# Crude secret-pattern scan
if git diff --cached -U0 | grep -E '(AWS_SECRET_ACCESS_KEY|API_KEY|PRIVATE_KEY|BEGIN [A-Z]+ PRIVATE KEY)=' >/dev/null; then
  echo "pre-commit: possible secret in staged diff — verify before committing" >&2
  exit 1
fi
```

## Validation Ladder Bootstrap

`docs/HARNESS.md § Future Validation Ladder` defines five command shapes. Before stage 8 starts, the project MUST have at least `validate:quick` runnable. The stack-selection decision should pick the framework; this playbook produces the script.

Minimum `validate:quick` (composition):

```text
format → lint → typecheck → unit tests → architecture check (if any)
```

Stack-specific examples:

| Stack | `validate:quick` shape |
| --- | --- |
| Node / TS | `pnpm format:check && pnpm lint && pnpm typecheck && pnpm test:unit` |
| Python | `ruff format --check && ruff check && mypy . && pytest tests/unit -q` |
| Go | `gofmt -l . && go vet ./... && golangci-lint run && go test -short ./...` |

Wire `validate:quick` into pre-commit (or pre-push) once it's reliable.

`test:integration`, `test:e2e`, `test:platform`, `test:release` ladder out as the project grows — add each when the first story actually needs it, not preemptively.

## Dev-Environment Setup

Document the **one-time setup** path in a top-level `README.md § Development` section after the stack lands. Shape:

```text
1. Install <runtime version> (e.g. Node 22 LTS, Python 3.12).
2. Install package manager (e.g. pnpm 9, uv).
3. Clone repo + cd in.
4. Copy .env.example → .env, fill in secrets from the vault.
5. <DB setup if needed> (e.g. start docker-compose, run migrations).
6. Run validate:quick to verify the toolchain.
7. Start the dev server.
```

The harness's `docs/QUICKSTART.md` covers the *harness* setup; the project's `README.md § Development` covers the *application* setup. Keep them separate.

## Implementation Guardrails (Reference)

`docs/templates/story.md § Implementation Guardrails` is the authority. Restated here for the agent reading this playbook at start of stage 8:

- Stay inside scope. Out-of-scope cleanup → new story or backlog row.
- Architecture change → new `docs/decisions/NNNN-*.md` before merging.
- Don't delete referenced code without grep proof.
- UI: handle loading + empty + error states, not just happy path.
- Input validation at the boundary (per `docs/ARCHITECTURE.md § Parse-First Boundary Rule`).
- Commit body explains change + cites at least one token.

## Variant Section

(Append a Variant block here when this playbook fails or partially works.)

## Related

- `docs/playbooks/solo-dev-client-delivery.md` § Stage 8 — this playbook IS the stage-8 detail.
- `docs/templates/story.md § Implementation Guardrails` — story-side rules this playbook enforces.
- `docs/playbooks/code-review-scoring.md` — stage 9 follows this playbook.
- `docs/HARNESS.md § Traceability Tokens` — token format authority.
- `docs/HARNESS.md § Future Validation Ladder` — script names this playbook bootstraps.
- `docs/templates/code-standards.md` — captures the per-stack choices that drive the pre-commit recipe.

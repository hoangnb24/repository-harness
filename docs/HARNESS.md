# Harness

The project goal is to provide a reusable operating harness that lets humans and
agents turn a future product spec into safe, validated work.

The app is what users touch. The harness is what agents touch.

## Mental Model

```text
------------------+
| Human intent    |
+------------------+
         |
         v
+------------------+
| Feature intake   |
+------------------+
         |
         v
+------------------+
| Story packet     |
+------------------+
         |
         v
+------------------+
| Agent work loop  |
+------------------+
         |
         v
+------------------+
| Product delta    |
+------------------+
         |
         v
+------------------+
| Validation proof |
+------------------+
         |
         v
+------------------+
| Harness delta    |
+------------------+
         |
         v
+------------------+
| Next intent      |
+------------------+
```

A change request can have two outputs:

1. Product delta: app code, tests, API shape, data model, or product docs.
2. Harness delta, when warranted: docs, templates, validation expectations,
   backlog items, or decision records that make the next change easier.

## Harness v0 Scope

Harness v0 includes:

- Agent entrypoint.
- Empty product documentation structure.
- Feature intake and risk lanes.
- Story templates.
- Decision log template.
- Validation report template.
- Test matrix placeholder.
- Harness growth backlog.
- Durable layer: SQLite database and CLI for operational records.

Harness v0 deliberately excludes:

- A project-specific `SPEC.md`.
- Pre-sliced product domains.
- A locked application stack.
- App source scaffolding.
- Package scripts.
- Test runner config.
- CI workflows.

Those should arrive only when a selected story needs them.

## Durable Layer

Policy documents describe how to work. The durable layer stores what happened.

Operational data — intake classifications, story status, decision outcomes,
backlog items, and execution traces — lives in a SQLite database (`harness.db`)
managed by the Rust Harness CLI at `scripts/bin/harness-cli`. Agents and humans
should use that binary for Harness work. The database is local to each project
instance and `.gitignore`d. The schema is version-controlled under
`scripts/schema/`.

This separation keeps policy docs stable and human-readable while giving agents
a structured, queryable record of operational state. It also prepares the
harness for future observability and automated evolution without adding more
markdown files.

Initialize the database if it does not exist:

```bash
scripts/bin/harness-cli init
```

Common commands:

```bash
scripts/bin/harness-cli intake  --type <type> --summary <text> --lane <lane>
scripts/bin/harness-cli story   add --id <id> --title <text> --lane <lane>
scripts/bin/harness-cli story   update --id <id> --status <status>
scripts/bin/harness-cli story   update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0
scripts/bin/harness-cli story   verify <id>
scripts/bin/harness-cli story   complete <id>
scripts/bin/harness-cli story   verify-all
scripts/bin/harness-cli decision add --id <id> --title <text> --doc docs/decisions/<file>.md
scripts/bin/harness-cli trace   --summary <text> --outcome <outcome>
scripts/bin/harness-cli score-trace
scripts/bin/harness-cli score-context <trace-id>
scripts/bin/harness-cli audit
scripts/bin/harness-cli propose
scripts/bin/harness-cli query   matrix
scripts/bin/harness-cli query   matrix --numeric
scripts/bin/harness-cli query   backlog
scripts/bin/harness-cli query   tools --summary
scripts/bin/harness-cli query   interventions
scripts/bin/harness-cli query   stats
scripts/bin/harness-cli --version
```

## Source Hierarchy

```text
User-provided spec or prompt
  input material for first buildout or future changes

docs/product/*
  current product contract derived from accepted input

docs/stories/*
  story-sized work packets and historical evidence

scripts/bin/harness-cli query matrix
  behavior-to-proof control panel backed by the durable layer

docs/decisions/*
  why the contract changed
```

Before implementation, product docs describe intent. After implementation,
product docs plus executable tests become the living contract.

## Spec Lifecycle

Harness v0 starts without a tracked project spec. When the human provides a
specification, treat it as input material, not as a permanent operating manual.
Use it to populate product docs, story packets, architecture decisions, and
validation expectations during the first buildout.

After the specification has been decomposed, do not keep extending it as the
living product plan. Ongoing work should update the smaller product docs,
stories, durable proof records, and decision records.

Ongoing work should enter the harness as one of these input types:

- New spec: a project specification that needs to become product docs and
  initial story candidates.
- Spec slice: a selected behavior from the provided spec.
- Change request: a bounded behavior change, bug fix, or product refinement.
- New initiative: a larger product area that needs multiple stories.
- Maintenance request: dependency, architecture, performance, security, or
  operational work.
- Harness improvement: a process, template, proof, or agent-instruction change.

The spec-to-work loop is:

```text
human intent or supplied spec
  -> classify input type
  -> update or create product contract
  -> create story packet or initiative notes when needed
  -> define validation proof
  -> implement or document the blocker
  -> update product docs, stories, durable proof records, and decisions
  -> capture harness friction
```

Large product areas should use scoped initiative notes instead of a second
monolithic specification. An initiative should explain the goal, affected
product docs, candidate stories, validation shape, open decisions, and exit
criteria. If initiative work becomes a repeated pattern, add a template or
record the proposal with `scripts/bin/harness-cli backlog add`.

## Growth Rule

The harness grows from friction.

When an agent is confused, repeats manual reasoning, needs a new validation
command, discovers a missing rule, or sees a recurring failure pattern, it must
either improve the harness directly or record the friction:

```bash
scripts/bin/harness-cli backlog add --title "<short name>" --pain "<what was hard>"
```

Use the backlog outcome loop for improvements that are expected to change agent
behavior or validation results:

1. When creating the backlog item, fill `--predicted` with the measurable
   impact expected from the improvement.
2. When closing the item, fill `--outcome` with the actual measured result or
   review evidence.
3. Use `scripts/bin/harness-cli query backlog --open` to review proposed and accepted
   items, and `scripts/bin/harness-cli query backlog --closed` to compare predictions
   with outcomes after implementation.

The `harness_friction` field on traces also captures per-task friction so
patterns can be queried later:

```bash
scripts/bin/harness-cli query friction
```

Backlog risk uses the same lane vocabulary as intake and stories:
`tiny`, `normal`, or `high-risk`. Use `--risk tiny` for low-risk follow-up
items; `low` is not a valid lane.

## Request-Class Loops

Classify authority before running Harness commands. The request class decides
whether repository state may change.

### Read-Only Requests

Answer, explain, review, diagnose, plan, and status requests are read-only.

1. Read `AGENTS.md` and only the files or evidence needed for the response.
2. Use read-only inspection commands when useful.
3. Do not run bootstrap, initialize or migrate a database, record intake,
   update stories or backlog, or record a trace.
4. Stop when the answer is supported by concrete repository evidence.

For example, a request to diagnose why an installer test fails may inspect the
test, installer, and captured output. It must not bootstrap a missing database
or create an intake row merely to explain the failure.

### Change Requests

Change, build, and fix requests authorize the normal Harness mutation loop:

1. Bootstrap the local ignored runtime with `scripts/bootstrap-harness.sh` on
   macOS/Linux or `.\scripts\bootstrap-harness.ps1` on Windows.
2. Classify the request with `docs/FEATURE_INTAKE.md` and record the
   classification with `scripts/bin/harness-cli intake`.
3. Check focused proof status with
   `scripts/bin/harness-cli query matrix --active --summary`, then use
   `scripts/bin/harness-cli query matrix --story <id>` if a story is selected.
4. Retrieve only the affected product, story, decision, and implementation
   files required by the selected lane in `docs/CONTEXT_RULES.md`.
5. Implement and validate inside that lane: tiny, normal, or high-risk.
6. Before finishing, ask whether product truth, validation expectations,
   architecture rules, repeated failure patterns, or next-agent instructions
   changed.
7. Record a trace with `scripts/bin/harness-cli trace`, using
   `docs/TRACE_SPEC.md` for the expected trace tier and field depth, and review
   the printed score.
8. If Harness friction was found, fix it in scope or record it with
   `scripts/bin/harness-cli backlog add`.

## Story Verification

Stories may carry a mechanical proof command:

```bash
scripts/bin/harness-cli story add --id US-012 --title "Story verification" --lane normal --verify "cargo test --workspace"
scripts/bin/harness-cli story update --id US-012 --verify "cargo test --workspace"
scripts/bin/harness-cli story verify US-012
```

`story verify` runs the command from the repository root, records
`last_verified_at` and `last_verified_result`, and exits 0 on pass or 1 on fail.
When `trace --story <id>` links to a story whose verification command has never
passed, the trace still records but prints an advisory warning before close.

Use `story verify-all` before merges, maturity claims, and benchmark runs. It
runs every configured story verification command, prints one result per story,
skips stories without `verify_command`, and exits 1 if any configured story
fails.

`story verify` accepts only the story id. Configure the command with
`story add --verify` or `story update --verify`. Record proof booleans with
`story update`, using numeric values: `1` means yes and `0` means no. The Rust
CLI rejects text values such as `yes` and `no`.

Use `scripts/bin/harness-cli query matrix --numeric` when copying proof values
back into `story update`. The default matrix output is human-readable
`yes`/`no`; the numeric output mirrors CLI input.

Use `query matrix --active --summary` to omit completed history and long
evidence text while retaining lane, runnable state, and proof columns.
`--runnable` uses the same planned/nonblank-verification/unblocked rule as
protocol story discovery, and `--story <id>` selects one exact story. Filters
combine with AND semantics. The unfiltered matrix remains the full durable
proof view.

`story complete <id>` is the explicit lifecycle transition for completed work.
It requires an `in_progress` or `changed` story, runs fresh proof, and marks the
story implemented only when that proof passes. Resolver stories additionally
require a stable linked Harness-improvement intake and a completed matching
implementation trace recorded after the newest resolver link. On pass, story
proof and eligible accepted backlog closures are committed atomically and
replayably. Ordinary text updates and JSON compare-and-set updates reject an
`implemented` target and direct the caller to `story complete`; other lifecycle,
proof, evidence, and verification-command updates remain available. Ordinary
`story verify` and `story verify-all` remain proof-only.

## Phase 5 Evolution Commands

Tool discovery:

```bash
scripts/bin/harness-cli query tools --summary
scripts/bin/harness-cli query tools --json
scripts/bin/harness-cli tool register --name <name> --command <cmd> --description <text> --responsibility Verification
```

Context and drift checks:

```bash
scripts/bin/harness-cli score-context <trace-id>
scripts/bin/harness-cli audit
```

`score-context` is advisory; it reports context-rule coverage without changing
the trace. `audit` reports drift categories and an entropy score documented in
`docs/HARNESS_AUDIT.md`.

Interventions are separate from traces:

```bash
scripts/bin/harness-cli intervention add --trace <id> --type correction --description <text> --source human
scripts/bin/harness-cli query interventions --story US-024
```

Record an intervention when a human, reviewer, CI system, or another agent
corrects, overrides, escalates, or approves work.

Improvement proposals:

```bash
scripts/bin/harness-cli propose
scripts/bin/harness-cli propose --accept <proposal-key> --outcome-after-traces 20
scripts/bin/harness-cli propose --reject <proposal-key> --reason "Not worth the added complexity"
```

`propose` prints deterministic, read-only proposals from repeated friction,
interventions, and audit drift. A human explicitly accepts one key with exactly
one outcome schedule or rejects one key with a reason. The old bulk
`--commit` path is rejected so displayed proposals cannot become accidental
work items.

## Decision Records

High-risk work needs durable decisions when it changes behavior or architecture.
For auth, authorization, data ownership, API shape, audit/security, or
validation changes, record the decision in both places:

1. Add a markdown file under `docs/decisions/` from
   `docs/templates/decision.md`.
2. Add or refresh the durable record:

```bash
scripts/bin/harness-cli decision add \
  --id 0008-auth-boundary \
  --title "Auth Boundary" \
  --doc docs/decisions/0008-auth-boundary.md \
  --notes "Accepted during T4 authentication work."
```

The trace `--decisions` field is useful evidence, but it is not the decision
log. Do not treat decision text in a trace as satisfying the durable decision
record requirement.

## Harness Change Policy

Agents may update directly:

- Non-completion story status and evidence via
  `scripts/bin/harness-cli story update`; use `story complete` to reach
  `implemented`.
- Test matrix rows via `scripts/bin/harness-cli story add` and
  `scripts/bin/harness-cli story update`.
- Links from story packets to product docs.
- Validation notes and reports.
- Small clarifications tied to the current task.
- Intake records, traces, and backlog items via `scripts/bin/harness-cli`.

Agents should ask for human confirmation before:

- Changing architecture direction.
- Removing validation requirements.
- Changing the source-of-truth hierarchy.
- Changing risk classification rules.
- Replacing the feature workflow.

## Done Definition

A read-only request is done when the response is supported by repository
evidence, clearly separates facts from inference, and leaves repository and
Harness state unchanged.

A change request is done only when:

- The requested change is completed or the blocker is documented.
- Relevant docs, stories, and test matrix entries remain current.
- Validation commands were run when they exist.
- A trace has been recorded with `scripts/bin/harness-cli trace`.
- Missing Harness capabilities were recorded with
  `scripts/bin/harness-cli backlog add` when relevant.
- The final response says what changed and what was not attempted.

## Future Validation Ladder

No validation scripts exist yet. When implementation begins, the expected ladder
is:

```text
validate:quick
  format, lint, typecheck, unit tests, architecture check

test:integration
  backend, database, provider, or service checks as the stack requires

test:e2e
  user-visible end-to-end flows

test:platform
  shell, mobile, desktop, or deployment smoke checks as the stack requires

test:release
  full suite, log checks, and performance smoke
```

Agents must not claim these commands pass until they exist and have been run.

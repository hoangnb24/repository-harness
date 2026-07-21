# repository-harness

Turn a software repository into a legible, agent-ready workspace.

`repository-harness` gives coding agents a small entrypoint, structured
repository knowledge, durable execution plans when work truly needs them, and
mechanical validation. The repository—not a hidden workflow database—is the
default system of record.

The app is what users touch. The harness is what makes the app and its rules
easy for agents and humans to understand.

## Why This Exists

Coding agents commonly fail for ordinary engineering reasons:

- important constraints live only in chat or in someone's head;
- the repository does not say which documents are authoritative;
- small changes are wrapped in process that obscures the actual work;
- large changes lose decisions and progress between sessions;
- validation is vague, late, or disconnected from user-visible behavior.

The answer is not a longer mandatory workflow. It is a repository that exposes
the right context at the right time and enforces important invariants with
tests and scripts.

This direction is anchored in OpenAI's
[Harness engineering](https://openai.com/index/harness-engineering/) account:
keep the agent entrypoint small, make repository knowledge navigable, store
complex execution plans durably, make application behavior directly
inspectable, and enforce architectural rules mechanically.

## The Default Workflow

Start with [`AGENTS.md`](AGENTS.md), then follow the map in
[`docs/WORKFLOW.md`](docs/WORKFLOW.md). The size of the request determines the
amount of durable process:

```text
read-only question
  -> inspect the smallest authoritative surface
  -> answer with evidence

bounded change
  -> inspect locally
  -> change code or docs
  -> run relevant proof
  -> report the result

multi-session or coordination-heavy change
  -> create docs/plans/active/<plan>.md
  -> record progress, decisions, and validation in Git
  -> move the finished plan to docs/plans/completed/

consequential ambiguity
  -> pause before mutation
  -> present the concrete choice and its effects
  -> continue after authority is clear
```

A typo fix does not need intake, a story row, or a trace. A migration spanning
several sessions does need a durable plan. A request to “simplify permissions”
without saying whether existing access may be revoked needs human judgment
before code changes. These are independent decisions, not risk levels on one
process ladder.

## Repository Knowledge

- [`AGENTS.md`](AGENTS.md) — compact, stable entrypoint for agents.
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — canonical request and execution flow.
- [`docs/HARNESS.md`](docs/HARNESS.md) — design principles and system model.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — boundaries and dependency
  direction.
- [`docs/product/`](docs/product/) — current product behavior and constraints.
- [`docs/plans/`](docs/plans/) — active and completed durable execution plans.
- [`docs/decisions/`](docs/decisions/) — durable architectural decisions.
- [`docs/templates/exec-plan.md`](docs/templates/exec-plan.md) — plan template.
- [`docs/README.md`](docs/README.md) — complete documentation map, including
  optional compatibility surfaces.

The default path requires no local database. Product documents, code, tests,
plans, decisions, and Git history form one inspectable source of truth.

## Install Harness Into A Project

From a target project directory, run:

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

On Windows PowerShell:

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.ps1"))) -Yes
```

Use `--merge` / `-Merge` to add missing Harness files without replacing
existing project files. Use `--override` / `-Override` only when replacement is
intentional. Use `--dry-run` / `-DryRun` to preview writes.

The default installation is the small repository-centered core. It does not
download a CLI, discover schemas, install bootstrap scripts, or add database
ignore rules. It also does not copy this upstream repository's README or
architecture over consumer-owned product truth.

For an older installation with a generated, long `AGENTS.md`, refresh it to the
small marked block:

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --merge --refresh-agent-shim --yes
```

For Claude Code, add `--claude` (PowerShell: `-Claude`). This creates or updates
a marked block in `CLAUDE.md` that imports `AGENTS.md`; existing local
instructions are preserved and backed up before changes.

## Try The Flow

[`docs/demo/README.md`](docs/demo/README.md) follows concrete examples through
the four workflow cases. The important cause and effect is simple:

- small entrypoint → less instruction loading and less drift;
- authoritative repository map → agents retrieve only relevant context;
- plans only for genuinely durable work → small changes stay cheap while long
  work survives session boundaries;
- repo-native tests → completion is proved by behavior rather than workflow
  bookkeeping;
- explicit pause conditions → consequential product choices remain human-owned.

## Optional Compatibility Control Plane

The Rust CLI, SQLite schema, feature intake, story matrix, trace scoring,
improvement proposals, and orchestration contract remain supported for an
external runner or team that explicitly selects them. They are not
prerequisites for ordinary repository work.

Install that complete compatibility bundle explicitly:

```bash
scripts/install-harness.sh --with-cli --yes /path/to/project
```

```powershell
./scripts/install-harness.ps1 -WithCli -Yes -Directory C:\path\to\project
```

Then bootstrap its ignored local database:

```bash
scripts/bootstrap-harness.sh
```

```powershell
.\scripts\bootstrap-harness.ps1
```

Then use `scripts/bin/harness-cli` (or the Windows `.exe`). See
[`scripts/README.md`](scripts/README.md) and
the [`compatibility index`](docs/compatibility/README.md).
One independent consumer is
[Symphony](https://github.com/hoangnb24/symphony); it is not installed as part
of this repository. Symphony owns work selection, agent runs, worktrees,
conflict/retry policy, changeset coordination, PR/review synchronization, and
its runtime evidence. Harness retains only the generic atomic protocol
primitives that protect repository state.

## Repository Structure

```text
project/
  AGENTS.md
  docs/
    WORKFLOW.md
    HARNESS.md
    ARCHITECTURE.md
    product/
    plans/
      active/
      completed/
    decisions/
    templates/
  scripts/
  tests/
```

## Contributing

See [the contributing guide](https://github.com/hoangnb24/repository-harness/blob/main/CONTRIBUTING.md).
Especially useful contributions are
real agent failure cases, examples of application legibility, mechanical
architecture checks, smaller default instructions, and validation that proves
user-visible behavior.

Short description:

> A repository-centered engineering harness for coding agents: compact
> instructions, navigable context, durable plans when needed, decisions, and
> executable validation.

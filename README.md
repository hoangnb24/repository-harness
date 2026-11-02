# repository-harness

Turn a software repository into a legible, agent-ready workspace.

`repository-harness` installs a small repository protocol and a safe updater.
The repository remains the system of record: product documents, decisions,
code, tests, CI, and runtime evidence define the work.

It is not a task database, story tracker, agent orchestrator, or application
runtime.

## What It Solves

Coding agents often fail for ordinary engineering reasons:

- important intent exists only in chat;
- the repository does not identify authoritative documents;
- small changes acquire unnecessary process;
- long changes lose decisions and recovery context;
- completion is claimed without behavior-level proof; and
- an agent invents product policy when the request leaves a material choice
  open.

Harness provides a compact entrypoint, a navigable repository map, optional
knowledge-discovery tools, and a safe maintenance binary.

## Repository Understanding

Find current behavior in code, types, interfaces, commands, tests, and examples.
Keep product intent and rationale where the repository already owns them.
Identify missing capabilities needed to act, observe, or verify, and report
uncertainty rather than inventing commands or claiming unsupported results.

Consumer repositories own task workflow and planning. Harness skills run only
when explicitly requested; installation does not activate them.

Start with [`AGENTS.md`](AGENTS.md) and the repository map in
[`docs/README.md`](docs/README.md).

## What Gets Installed

The default core contains:

- a compact `AGENTS.md` entrypoint;
- repository context and navigation;
- optional product, decision, and execution-plan locations;
- optional templates for durable plans, decisions, application runbooks, and
  evidence-backed Harness improvements; and
- an invariant-encoding reference and explicit-only skills for discovery,
  audit, encoding, and improvement.

It does not install application architecture, product policy, validation
commands, credentials, a database, schemas, orchestration, or background
processes.

The exact payload is declared in
[`scripts/harness-install-files.txt`](scripts/harness-install-files.txt).

## Install

From a target repository:

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh?$(date +%s)" |
  bash -s -- --yes
```

On PowerShell:

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.ps1"))) -Yes
```

Use `--merge` / `-Merge` to preserve existing files and add only missing
Harness paths. Use `--override` / `-Override` only when replacement is
intentional. Use `--dry-run` / `-DryRun` to preview.

The bootstrap downloads a versioned `harness` binary and checksum, verifies
release identity, and delegates installation to that candidate.

## Maintain An Installation

```bash
scripts/bin/harness status
scripts/bin/harness doctor
scripts/bin/harness update --dry-run
scripts/bin/harness update
```

The updater stores the exact upstream base under `.harness-core/`, performs a
three-way merge, backs up changed files, and activates the result
transactionally.

If local and upstream edits overlap, no managed file or executable changes.
Harness retains BASE, LOCAL, UPSTREAM, and RESOLVED copies plus the frozen
managed input set. After a human resolves the semantic choice:

```bash
scripts/bin/harness update --continue --dry-run
scripts/bin/harness update --continue
```

Use `scripts/bin/harness update --abort` to discard only the staged resolution.

## Measure Skill Use

```bash
scripts/bin/harness skill-report ~/.claude/projects/<project>/<session>.jsonl
```

`skill-report` is read-only and runs only when invoked. It reads the Claude
Code session files you name and reports, per explicitly invoked skill,
invocations, `HARNESS_SKILL:` receipts, and input, cache-creation, cache-read,
and output tokens (`--json` for machines). It prints aggregates only, writes
nothing, and rejects other session formats. Receipts are self-reported, so the
report measures format compliance, not whether the work was correct.

## Optional Skills

Invariant enforcement routes accepted rules through repository-native
validation:

```text
$encode-invariant
```

Brownfield onboarding is explicit and read-only first:

```text
$onboard-repository
```

Harness improvement is also explicit and requires baseline-to-rerun evidence:

```text
$improve-harness
```

Engineering advice is a separate opt-in payload:

```bash
scripts/install-harness.sh --with-engineering-wisdom --yes /path/to/project
```

All Harness skills require explicit user invocation, including invariant
encoding. No skill runs during installation or merely because a request
matches its subject matter.

## What We Prove

Harness owns three release-evidence boundaries:

1. **Fresh installation:** the declared core is installed without fabricated
   application truth or hidden lifecycle state.
2. **Repository navigation:** an agent follows repository authority, avoids
   speculative product policy, and can stop at a real decision boundary.
3. **Safe maintenance:** updates verify identity and checksum, preserve local
   edits, stage conflicts, reject drift, and recover interrupted transactions.

Operating an arbitrary consumer application end to end remains consumer-owned
research. Harness does not claim that installation alone supplies runtimes,
fixtures, credentials, logs, or interface automation.

## Protocol V1 End Of Life

The former SQLite `harness-cli` and machine protocol v1 ended support on
2026-08-10. The last published compatibility release is
`harness-cli-v0.1.22`. Existing consumers may pin that immutable release, but
the current repository no longer builds, installs, tests, or publishes it.

Harness does not automatically delete legacy binaries, databases, schemas, or
state from consumer repositories.

See
[`decision 0027`](docs/decisions/0027-end-protocol-v1-and-focus-repository-protocol.md).

## Development

```bash
scripts/validate-premerge.sh
```

The contract runs Rust formatting, tests, Clippy, installer and workflow
checks, release guards, documentation checks, shell syntax, and
`git diff --check`.

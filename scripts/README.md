# Scripts

This directory contains harness automation tools.

## Harness CLI

The Rust Harness CLI is the primary interface for the durable layer. Installed
projects use the prebuilt binary at `scripts/bin/harness-cli` on macOS/Linux or
`scripts/bin/harness-cli.exe` on Windows for normal Harness work.

Request authority comes before runtime setup. Answer, explain, review,
diagnose, plan, and status requests remain read-only: inspect what is already
present, and do not bootstrap, initialize/migrate, record intake, or trace.

For a change, build, or fix request after a fresh clone or install, bootstrap
the local ignored runtime before querying or changing state:

```bash
scripts/bootstrap-harness.sh
```

```powershell
.\scripts\bootstrap-harness.ps1
```

In this source repository, bootstrap builds the CLI from the checked-out Rust
source so code and command behavior cannot drift. It refuses to invent an empty
replacement when the default core database is missing, and it rejects a
schema-current database that still contains product-owned state. Restore the
verified core epoch in that case. In an installed consumer it uses the
checksum-verified prebuilt binary and safely initializes a missing local
database. Both modes migrate older supported databases and refuse unsupported
schemas or CLI/release-pin drift.

```bash
scripts/bin/harness-cli init          # Create the database
scripts/bin/harness-cli intake ...    # Record a feature intake classification
scripts/bin/harness-cli story ...     # Add or update a story (test matrix row)
scripts/bin/harness-cli story update --id US-001 --unit 1 --integration 1 --e2e 0 --platform 0
scripts/bin/harness-cli story verify US-001  # Run the story's verify_command
scripts/bin/harness-cli story complete US-001 # Fresh proof plus atomic lifecycle completion
scripts/bin/harness-cli decision ...  # Add a decision or run its verification
scripts/bin/harness-cli backlog ...   # Add or close a backlog item
scripts/bin/harness-cli propose       # Classify new, active, handled, and recurring evidence
scripts/bin/harness-cli propose --show-suppressed # Explain handled evidence
scripts/bin/harness-cli trace ...     # Record and auto-score an agent execution trace
scripts/bin/harness-cli score-trace   # Score a trace against TRACE_SPEC.md tiers
scripts/bin/harness-cli query ...     # Query harness data, including backlog --open/--closed
scripts/bin/harness-cli query matrix --numeric  # Show proof flags as 1/0
scripts/bin/harness-cli query matrix --active --summary  # Focus on unfinished work without evidence text
scripts/bin/harness-cli query matrix --runnable --summary # Show work ready under protocol-v1 rules
scripts/bin/harness-cli query matrix --story US-001      # Inspect one exact story
scripts/bin/harness-cli db changeset apply .harness/changesets/run_123.changeset.jsonl
scripts/bin/harness-cli db rebuild --from .harness/changesets
scripts/bin/harness-cli migrate       # Apply pending schema migrations
scripts/bin/harness-cli --version     # Print the installed CLI version
```

Run `scripts/bin/harness-cli help` or `scripts/bin/harness-cli query help` for
full usage. On Windows, use the same commands through
`.\scripts\bin\harness-cli.exe`.

Proof flags on `story update` are numeric booleans: use `1` for yes and `0` for
no. `story verify <id>` runs the configured `verify_command`; it does not accept
proof flags. Configure the command with `story add/update --verify`, run
`story verify <id>`, then update proof flags with `story update`.

`story update --status implemented` is rejected in both human-readable and
JSON/CAS modes. Move active work to `in_progress` or `changed`, then use `story
complete <id>` so fresh proof and the implemented transition happen together.

Backlog `--risk` uses Harness lanes, not severity words: use `tiny`, `normal`,
or `high-risk`. Use `tiny` instead of `low`. `query matrix` defaults to
human-readable `yes`/`no`; use `query matrix --numeric` when copying values into
`story update`. Matrix filters combine with AND semantics: `--active` keeps
`planned`, `in_progress`, and `changed` stories; `--runnable` uses the same rule
as protocol story discovery; `--story <id>` selects one exact ID. `--summary`
omits the potentially long evidence column while keeping lane and runnable
state. With none of these flags, the existing full matrix output is unchanged.

The schema lives in `scripts/schema/` and is version-controlled. The database
file (`harness.db`) is `.gitignore`d.

Repository maintainers can run `scripts/verify-revision-coherence.sh` to prove
that crate, lockfile, pinned-release, migration, protocol, bootstrap, replay,
and public-command contracts describe the same revision.

Set `HARNESS_DB_PATH=/path/to/harness.db` when a workflow needs `harness-cli`
to operate on an isolated copied database. `HARNESS_DB_PATH` takes precedence
over the legacy `HARNESS_DB` override; if neither is set, the CLI uses
`harness.db` in the repository root.

Set `HARNESS_RUN_ID=<run-id>` during an isolated run to append semantic
operation records to `.harness/changesets/<run-id>.changeset.jsonl` under the
resolved repository root. The first write records a `changeset.header`; durable
write commands append operation records such as `story.update`, `trace.add`,
and `decision.add`. Normal CLI use without `HARNESS_RUN_ID` writes no
changeset.

Requires: the prebuilt Rust CLI at `scripts/bin/harness-cli` on macOS/Linux or
`scripts/bin/harness-cli.exe` on Windows.

Direct database inspection may still use SQLite tools, but normal Harness use
should go through the Rust CLI.

### Rust CLI Commands

Current migrated commands:

```bash
scripts/bin/harness-cli init
scripts/bin/harness-cli migrate
scripts/bin/harness-cli import brownfield
scripts/bin/harness-cli intake ...
scripts/bin/harness-cli story add ...
scripts/bin/harness-cli story update ...
scripts/bin/harness-cli story verify ...
scripts/bin/harness-cli story complete ...
scripts/bin/harness-cli decision add ...
scripts/bin/harness-cli decision verify ...
scripts/bin/harness-cli backlog add ...
scripts/bin/harness-cli backlog close ...
scripts/bin/harness-cli trace ...
scripts/bin/harness-cli score-trace
scripts/bin/harness-cli query matrix
scripts/bin/harness-cli query backlog
scripts/bin/harness-cli query decisions
scripts/bin/harness-cli query intakes
scripts/bin/harness-cli query traces
scripts/bin/harness-cli query friction
scripts/bin/harness-cli query stats
scripts/bin/harness-cli query sql ...
scripts/bin/harness-cli db changeset apply ...
scripts/bin/harness-cli db rebuild --from ...
```

`query sql` accepts one read-only SQLite statement. The CLI enforces read-only
access at the database connection, including for CTEs, pragmas, and statements
with `RETURNING`; use typed Harness mutation commands, migrations, or semantic
changesets for writes.

`scripts/bin/harness-cli import brownfield` seeds or refreshes the durable database
from existing Harness v0 markdown in `docs/TEST_MATRIX.md`,
`docs/decisions/`, and `docs/HARNESS_BACKLOG.md`. This keeps already-installed
Harness repos on the Rust CLI path without losing their populated operating
docs.

## Installer

Phase 7 also has separate, unpromoted V1 artifact installers:
`scripts/install-harness-v1.sh` and `scripts/install-harness-v1.ps1`. They take
an already-downloaded native artifact, an externally supplied exact checksum
record, a platform label, and a target directory. They verify the checksum
before platform selection. Bash can copy to `scripts/bin/harness`; PowerShell
returns deterministic controlled unsupported before destination creation or
publication because safe Windows handle-relative/no-follow publication is not
implemented. Neither installer executes the artifact. A checksum proves
byte integrity against that record; it does not authenticate provenance or
authorize a release. These V1 surfaces do not change the public V0 installer
below and remain non-production until US-112's external gates close.
Bash rejects a linked target root, `scripts`, or `scripts/bin` before copying
and publishes relative to a physically pinned `bin` directory. PowerShell does
not inspect or create the destination tree and contains no copy/move path; its
controlled-unsupported result remains a Phase 7 Windows blocker.

The Phase 7 diagnostic workflow supplies the separate provenance gate. It
finalizes artifact bytes, generates GitHub/Sigstore build provenance with the
exact-pinned action in an isolated non-executing job, verifies the retained
signed bundle in a separate read-only job, and only then permits
help, installer, or direct-binary execution. Build/execution receipts bind the
artifact, bundle, verification record, repository, workflow path/ref, and exact
candidate/workflow SHA. Verification uses exact `--cert-identity` without the
mutually exclusive `--signer-workflow` flag. Workflow Python calls use the
setup-python output explicitly. The privileged job also pins artifact download
to v8.0.1 commit `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` and
bundle upload to v7.0.1 commit `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`;
moving artifact refs remain only in read-only jobs. Candidate subprocesses use
a fresh minimal allowlist with launch/temp/locale/Windows essentials and exact
trusted `HARNESS_V1_*` bindings. GitHub command files, Actions/OIDC state,
tokens, Python injection, home, and cache variables are not inherited. This
candidate boundary is separate from the trusted `gh` verifier, whose temporary
home/config/state/cache root is deleted after verification to keep its local
bookkeeping outside the checkout. The diagnostic attestation uses no stored
key and does
not authorize platform acceptance, production signing, publishing, or
promotion.

The upstream installer applies the Harness v0 operating files and folder
structure to a target project directory. It defaults to the current directory,
accepts a target path, and asks interactive users whether to `1. Merge`,
`2. Override`, or `3. Stop` when the target already contains `AGENTS.md`,
`docs/`, or `scripts/`.
Non-interactive installs stop on those protected paths unless `--merge` or
`--override` is provided. Use `--merge` as the safe update path for repositories
that already have Harness: it keeps existing files in place and creates only
missing Harness files. Add `--refresh-agent-shim` when an older install has the
full generated Harness guide in `AGENTS.md` and should move to the small stable
shim. Use `--override` only when replacing the protected Harness surface is
intentional.

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.ps1"))) -Yes
```

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --merge --yes
```

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.ps1"))) -Merge -Yes
```

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --merge --refresh-agent-shim --yes
```

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.ps1"))) -Merge -RefreshAgentShim -Yes
```

`--refresh-agent-shim` backs up `AGENTS.md` before changing it. If the existing
file is recognized as the old Harness-generated operating guide, the installer
replaces it with the current shim. Otherwise it appends or replaces only the
marked `<!-- HARNESS:BEGIN -->` block so project-specific instructions remain
in place. Both installers read that block from
`scripts/agent-harness-block.md`; the Bash `--claude` path reads
`scripts/claude-harness-block.md`, whose only import is `AGENTS.md`. This keeps
root, fresh-install, and refresh behavior on the same authority text.

`--upgrade-cli` (PowerShell: `-UpgradeCli`) also refreshes the marked
`AGENTS.md` Harness block. This prevents a new binary from retaining stale
request authority while preserving text outside the marked block and creating
the normal backup. It does not overwrite arbitrary custom documentation.

The installer must stay limited to harness files. Do not use it to scaffold
application source folders, package scripts, CI, tests, platform shells, or fake
validation commands. The installer script is not part of the installed project
payload.

The file payload is declared once in `scripts/harness-install-files.txt` and is
read by both the Bash and PowerShell installers. Add new Harness docs,
templates, or decisions there instead of duplicating file lists in each
installer. Schema migrations are different: both installers discover
`scripts/schema/*.sql` automatically from the source repository, so adding a
new migration only requires committing the SQL file.

By default the installer also downloads the prebuilt Rust Harness CLI for the
current platform into `scripts/bin/harness-cli` on macOS/Linux or
`scripts/bin/harness-cli.exe` on Windows, then verifies its `.sha256` checksum.
A source branch can pin the release used by the installer through
`scripts/harness-cli-release-tag`; Phase 3 pins `harness-cli-v0.1.4` so branch
installs receive a Phase 3-built CLI. Set `HARNESS_CLI_RELEASE_TAG` to override
that tag, or set `HARNESS_CLI_BASE_URL` to point at an alternate artifact
directory, such as a local `file:///.../dist` directory created by
`scripts/build-harness-cli-release.sh`.

`--merge` (PowerShell: `-Merge`) deliberately does not replace an existing CLI.
To upgrade a CLI explicitly, pin one immutable tag for both the template files
and release artifact:

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/harness-cli-v0.1.14/scripts/install-harness.sh" |
  bash -s -- --merge --upgrade-cli --ref harness-cli-v0.1.14 --yes
```

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/hoangnb24/repository-harness/harness-cli-v0.1.14/scripts/install-harness.ps1"))) `
  -Merge -UpgradeCli -Ref harness-cli-v0.1.14 -Yes
```

The installer rejects branch names and `latest`, downloads the tagged template
and matching platform artifact, verifies the published SHA-256, backs up the
old executable, then atomically replaces it. A download/checksum failure leaves
the old CLI in place. Run `scripts/test-install-harness-cli-upgrade.sh` for the
merge/upgrade/checksum-preservation regression.

The external process protocol, including JSON envelopes, capability discovery,
timeouts, and snapshot semantics, is documented in
`docs/contracts/harness-orchestration-v1.md`.

## Schema Migrations

Migration files live under `scripts/schema/` and are named `NNN-description.sql`
where `NNN` is a zero-padded version number. Run `scripts/bin/harness-cli migrate` to
apply pending migrations.

## Pre-Merge Validation Contract

Repository maintainers and pull-request CI run the same release-relevant gate:

```bash
scripts/validate-premerge.sh
```

It checks Rust formatting, tests, and linting; revision/schema/command
coherence; bootstrap, protocol, installer, documentation, and representative
task-effect contracts; release workflow structure; and whitespace errors.
Installed consumer projects keep their own stack-specific validation commands;
the template does not impose this repository's Rust gate on them.

The V1 implementation gates are also individually runnable:

```bash
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
```

The Phase 3 gate runs the complete `harness-core` test target and an eleven-group
mechanical verifier for exact preview/write binding, authenticated recovery
ownership, manifest-last durability, kill points, idempotency, read-only status
probing, platform fail-closed behavior, and the closed Phase 4/7 boundaries.

The Phase 4 gate runs the archive-only bridge tests and ten executable proof
groups: exact four-command grammar; schemas 1–13; WAL-aware live/archive export;
unique no-replace publication; foreign custody preservation; tamper rejection;
SQLite-free six-command core receipt recovery; Windows controlled unsupported
exit 5; unpromoted lifecycle state; and immutable tracked fixture bytes.

## Changeset Rebuild Validation

Run the durable repository rebuild and its validator contract regressions:

```bash
scripts/validate-changeset-rebuild.sh
scripts/test-validate-changeset-rebuild.sh
```

The validator builds the current workspace CLI unless `HARNESS_CLI` is set
explicitly. `HARNESS_CHANGESET_DIR` can point validation at a copied fixture
history without changing the repository changesets.

## Release Packaging

Build the current-platform Rust CLI release artifact from the source repo:

```bash
scripts/build-harness-cli-release.sh
```

The script writes `dist/harness-cli-<platform>` plus `.sha256` checksums. The
Windows artifact includes the `.exe` suffix. Supported labels are:

- `macos-arm64`
- `macos-x64`
- `linux-x64`
- `linux-arm64`
- `windows-x64`

For cross-compilation, pass a Cargo target triple:

```bash
scripts/build-harness-cli-release.sh --target x86_64-unknown-linux-gnu
```

GitHub releases are produced by
`.github/workflows/harness-cli-release.yml`. Post-merge automation or an
explicit manual dispatch supplies a desired `harness-cli-v*` tag and an exact
main-branch source ref. The workflow verifies the untagged candidate, builds all
supported targets on native hosted runners, and creates the annotated tag only
after every platform and upgrade-transition check passes. It then publishes
these release assets without overwriting an existing release:

- `harness-cli-macos-arm64`
- `harness-cli-macos-arm64.sha256`
- `harness-cli-macos-x64`
- `harness-cli-macos-x64.sha256`
- `harness-cli-linux-x64`
- `harness-cli-linux-x64.sha256`
- `harness-cli-linux-arm64`
- `harness-cli-linux-arm64.sha256`
- `harness-cli-windows-x64.exe`
- `harness-cli-windows-x64.exe.sha256`

Merged PRs are handled by `.github/workflows/post-merge-maintenance.yml`. The
workflow always prepends a PR summary to `CHANGELOG.md`. If the merged PR
changed CLI source, schema, Cargo metadata, or release proof/promotion
packaging, it also increments the CLI patch version, updates
`scripts/harness-cli-release-tag`, and calls the reusable workflow with the
exact maintenance commit. The old `v0.1.14` upgrade source is checked against a
frozen historical contract; the built and installed candidate are checked
against the current strict contract. A failed tag is consumed and immutable,
so recovery advances to a later patch version.

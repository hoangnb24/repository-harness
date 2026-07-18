# Rehearsal Preflight Transcript

## Pinned Worktree

```text
pwd
/Users/tubakhuym/.herdr/worktrees/e-inna-brain/agent-phase5-pilot-einna

git rev-parse HEAD
9be2b9b624f29c2c4f93bb576485fd8de2085af4

git status --short --untracked-files=all
<empty>
```

## Required Harness Query Before Action

```text
scripts/bin/harness-cli query matrix
zsh: no such file or directory: scripts/bin/harness-cli
exit 127
```

Cause and effect: the repository instructions require the Rust CLI, but the
pinned Git tree contains only `scripts/README.md`, product scripts, and schema
files under `scripts/`; there is no `scripts/bin/harness-cli`. Therefore the
matrix could not be queried and no durable intake/trace/audit row could be
recorded through the repository-native Harness.

## Offline Dependency Restore Before Lock

The shell initially exposed no `node` on `PATH`. Local inspection found Node
`22.22.3`, Node `26.0.0`, pnpm `11.11.0`, and a cached pnpm `10.30.1`. No Node
24 runtime was present. The package contract requires Node `>=24 <25` and pnpm
`>=10 <11`, so the cached pnpm was paired with Node 22 and the mismatch was
retained explicitly.

```text
pnpm install --frozen-lockfile --offline
WARN Unsupported engine: wanted Node >=24 <25; current Node v22.22.3, pnpm 10.30.1
Lockfile is up to date, resolution step is skipped
Packages: +472
resolved 472, reused 472, downloaded 0, added 472
Done in 1.7s using pnpm v10.30.1
exit 0
```

This setup happened before the environment lock at `2026-07-18T06:30:33Z`.
It changed only ignored `node_modules/` state and made no tracked-file change.

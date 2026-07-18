# Native Harness Queries Before Action

Working directory:
`/Users/tubakhuym/.herdr/worktrees/harness-benchmark/agent-phase5-pilot-benchmark`

The mandated matrix query was the first native Harness operation:

```text
$ scripts/bin/harness-cli query matrix
zsh:1: no such file or directory: scripts/bin/harness-cli
exit_code=127
```

The repository contains no `scripts/bin` directory. Capability discovery was
attempted before using related local feedback surfaces:

```text
$ scripts/bin/harness-cli query tools --capability impact-analysis --status present
zsh:1: no such file or directory: scripts/bin/harness-cli
exit_code=127

$ scripts/bin/harness-cli query tools --capability coverage --status present
zsh:1: no such file or directory: scripts/bin/harness-cli
exit_code=127

$ scripts/bin/harness-cli query tools --capability documentation-lookup --status present
zsh:1: no such file or directory: scripts/bin/harness-cli
exit_code=127

$ scripts/bin/harness-cli query tools --capability security-scan --status present
zsh:1: no such file or directory: scripts/bin/harness-cli
exit_code=127

$ scripts/bin/harness-cli query tools --capability performance-benchmark --status present
zsh:1: no such file or directory: scripts/bin/harness-cli
exit_code=127
```

Cause and effect: the native entrypoint named by `AGENTS.md` is absent, so the
matrix, tool-registry, intake, story, trace, audit, intervention, and proposal
operations cannot run. Rebuilding or copying a CLI from another checkout would
change the locked evaluation subject and was not attempted. Repository-native
Git, npm, TypeScript, and Vitest feedback remain available under the environment
lock.

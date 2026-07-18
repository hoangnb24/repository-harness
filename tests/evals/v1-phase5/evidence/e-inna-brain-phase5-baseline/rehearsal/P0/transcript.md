# P0 Rehearsal Transcript

Start and completion: `2026-07-18T06:33:02Z`.

## Exact Subject Identity

```text
git rev-parse HEAD
9be2b9b624f29c2c4f93bb576485fd8de2085af4
exit 0

git rev-parse HEAD^{tree}
710109132b01f503e6ad2c1664040004c87900ce
exit 0
```

## Manifest, Status, And Audit

```text
scripts/bin/harness-cli query tools --json
zsh: no such file or directory: scripts/bin/harness-cli
exit 127

scripts/bin/harness-cli query matrix
zsh: no such file or directory: scripts/bin/harness-cli
exit 127

scripts/bin/harness-cli audit
zsh: no such file or directory: scripts/bin/harness-cli
exit 127

git diff --check
exit 0
```

## Result

Outcome: `failed` with readiness `unresolved`.

The useful target-owned paths were mapped in place and every selected before
and after digest is identical. However, the installed operational subject is
structurally incomplete: the documented CLI path does not exist, so its tool
manifest, durable status, and audit cannot run. Reporting `ready` would violate
P0; no missing binary was fabricated or copied from another repository.

# P0 Install or Brownfield Adoption Evidence

Outcome: `passed` with readiness `unresolved`.

The evaluation subject is the pre-candidate baseline at commit
`090f6d1c33d9f006cc8e95491badc33a8053c89f`, captured by
`repository.bundle` (SHA-256
`8bf677d9c40e50ea02da38322b4a21fe59bd94f55d77ab417b7ea31a73a090a3`).
`git bundle verify` resolved that exact commit as `HEAD` and reported a complete
history.

## Selected path mapping

All selected paths are `target-owned`, retained in place, active, and governed
by `never-auto-patch` during adoption.

| Role | Path | Before SHA-256 | After SHA-256 | Result |
| --- | --- | --- | --- | --- |
| agent entrypoint | `AGENTS.md` | `ddcabaad867731b3c243633470950af5c10546f2a1d0d0cb3cd57dfacc139298` | `ddcabaad867731b3c243633470950af5c10546f2a1d0d0cb3cd57dfacc139298` | identical |
| project readme | `README.md` | `df9f67a1652a41d8e5d8661f000e4d811f734fd66d4c842e51966d13bbf48574` | `df9f67a1652a41d8e5d8661f000e4d811f734fd66d4c842e51966d13bbf48574` | identical |
| Harness policy | `docs/HARNESS.md` | `03409eff6ede225036036ab412e3357a887cbf2f192b2ccdd4644abdeeed7793` | `03409eff6ede225036036ab412e3357a887cbf2f192b2ccdd4644abdeeed7793` | identical |
| feature intake | `docs/FEATURE_INTAKE.md` | `7ac3edbe446f1373e0437bcc80d6b3de4debf4f144f687decd11a939362f8cda` | `7ac3edbe446f1373e0437bcc80d6b3de4debf4f144f687decd11a939362f8cda` | identical |
| architecture | `docs/ARCHITECTURE.md` | `4fdcce3aa30b1f453bfae9703cd212eec7c24a53ccf6cf53487d9071bb23a33b` | `4fdcce3aa30b1f453bfae9703cd212eec7c24a53ccf6cf53487d9071bb23a33b` | identical |
| context rules | `docs/CONTEXT_RULES.md` | `315564242eb45c5e3a38b9823273204ca8fdf058c8b1fec084957f12004c1be8` | `315564242eb45c5e3a38b9823273204ca8fdf058c8b1fec084957f12004c1be8` | identical |
| tool registry | `docs/TOOL_REGISTRY.md` | `83f1393156f61b8e5a5b73c37aba1ef6c1f1e82eca0210643266c1db9c638876` | `83f1393156f61b8e5a5b73c37aba1ef6c1f1e82eca0210643266c1db9c638876` | identical |
| proof matrix | `docs/TEST_MATRIX.md` | `f02edb3a091e370faec80f102c4fee456d7a5e729f6faa4e7dd7751b95b709a0` | `f02edb3a091e370faec80f102c4fee456d7a5e729f6faa4e7dd7751b95b709a0` | identical |
| trace contract | `docs/TRACE_SPEC.md` | `8adae6b814352fb1d4a53121db0b23643d99cee018ecb1281244e9b90bfc9018` | `8adae6b814352fb1d4a53121db0b23643d99cee018ecb1281244e9b90bfc9018` | identical |
| component map | `docs/HARNESS_COMPONENTS.md` | `18fd9c3d406922764c1cd029d7e7073f9ac63fc7fe916d65dc9040353fced8ca` | `18fd9c3d406922764c1cd029d7e7073f9ac63fc7fe916d65dc9040353fced8ca` | identical |
| maturity ladder | `docs/HARNESS_MATURITY.md` | `9eb2cb42fe5f22e00592322198554b1b6fcd124787bc5a38db4988552ba60751` | `9eb2cb42fe5f22e00592322198554b1b6fcd124787bc5a38db4988552ba60751` | identical |
| benchmark protocol | `benchmark/PROTOCOL.md` | `512bb9325ebe2f75485c465e6df66c33379484ec2db996196a6991dcad5fe9b2` | `512bb9325ebe2f75485c465e6df66c33379484ec2db996196a6991dcad5fe9b2` | identical |

## Exact transcript

```text
$ git bundle create docs/evidence/phase5-pilot-benchmark/repository.bundle 090f6d1c33d9f006cc8e95491badc33a8053c89f
fatal: Refusing to create empty bundle.
exit_code=128

$ git bundle create docs/evidence/phase5-pilot-benchmark/repository.bundle HEAD
exit_code=0

$ git bundle verify docs/evidence/phase5-pilot-benchmark/repository.bundle
docs/evidence/phase5-pilot-benchmark/repository.bundle is okay
The bundle contains this ref:
090f6d1c33d9f006cc8e95491badc33a8053c89f HEAD
The bundle records a complete history.
The bundle uses this hash algorithm: sha1
exit_code=0

$ git status --porcelain=v1
?? docs/evidence/
exit_code=0

$ scripts/bin/harness-cli audit
zsh:1: no such file or directory: scripts/bin/harness-cli
exit_code=127

$ git diff --no-ext-diff --check
exit_code=0
```

Cause and effect: the existing target-owned knowledge paths were adopted in
place, so all before/after digests remain identical. The installed Rust subject
is absent, so readiness is `unresolved`, not guessed `ready`; the missing audit
surface is a blocker but does not hide the structurally correct adoption.

The final-baseline rerun at `2026-07-18T07:11:47Z` repeated `git bundle verify`
(exit 0), `scripts/bin/harness-cli audit` (exit 127, entrypoint absent), and the
locked `git diff --no-ext-diff --check` acceptance command (exit 0).

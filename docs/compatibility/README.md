# CLI Compatibility Index

This source-only index is for explicit users and maintainers of the Rust CLI,
SQLite durable layer, or orchestration protocol. None of these operations is a
prerequisite for ordinary repository work.

## Install Boundary

Select the complete compatibility bundle explicitly:

```bash
scripts/install-harness.sh --with-cli --yes /path/to/project
```

```powershell
./scripts/install-harness.ps1 -WithCli -Yes -Directory C:\path\to\project
```

That profile adds the lifecycle references, bootstrap scripts, full schema
history, local database/binary ignore rules, release metadata, and one
checksum-verified platform binary. `--upgrade-cli` / `-UpgradeCli` implies this
profile and requires an immutable release reference.

## Lifecycle References

- [Phase 4 write-consumer inventory and freeze boundary](phase-4-write-consumer-inventory.md)
- [Superseded Phase 3 active-observability plan](phase-3-active-observability-legacy.md)
- [Superseded Phase 4 mechanical-verification roadmap](phase-4-mechanical-verification-legacy.md)
- [Superseded Phase 5 evolution-infrastructure roadmap](phase-5-evolution-infrastructure-legacy.md)
- [Feature intake](../FEATURE_INTAKE.md)
- [Story proof matrix](../TEST_MATRIX.md)
- [Trace and scoring](../TRACE_SPEC.md)
- [Audit](../HARNESS_AUDIT.md)
- [Backlog](../HARNESS_BACKLOG.md)
- [Components](../HARNESS_COMPONENTS.md)
- [Maturity model](../HARNESS_MATURITY.md)
- [Improvement protocol](../IMPROVEMENT_PROTOCOL.md)
- [Tool registry](../TOOL_REGISTRY.md)
- [Legacy stories](../stories/README.md)

## Runtime And Orchestration

- [Protocol v1](../contracts/harness-orchestration-v1.md)
- [Phase 5 ownership boundary](../decisions/0023-optional-consumer-ownership.md)
- [Symphony](https://github.com/hoangnb24/symphony) owns scheduling, agent runs,
  worktrees, conflict/retry policy, PR/review synchronization, and
  Symphony-specific runtime evidence.
- [Upstream CLI and bootstrap operations](../../scripts/README.md)
- Schema migrations: `scripts/schema/*.sql`
- Bootstrap: `scripts/bootstrap-harness.sh` or
  `scripts/bootstrap-harness.ps1`

Existing databases and binaries remain local and are never removed by an
ordinary core install or refresh.

The protocol supplies consumer-neutral atomic operations; it does not make
Symphony orchestration policy part of Harness. Trace scoring, benchmark,
audit, and proposal documents on this index remain legacy compatibility
material, not a default evaluation workflow.

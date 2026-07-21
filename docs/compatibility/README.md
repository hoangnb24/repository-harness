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
- [Upstream CLI and bootstrap operations](../../scripts/README.md)
- Schema migrations: `scripts/schema/*.sql`
- Bootstrap: `scripts/bootstrap-harness.sh` or
  `scripts/bootstrap-harness.ps1`

Existing databases and binaries remain local and are never removed by an
ordinary core install or refresh.

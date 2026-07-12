# US-081 Validation Subprocess Write Quarantine

## Status

implemented

## Lane

normal

## Product Contract

Harness verification subprocesses must run without the active orchestrated run's
operation-log environment. Their tests and fixture CLI writes must not append
unrelated operations to the active story changeset; the Harness CLI's own
post-verification proof record remains a legitimate run operation.

## Relevant Product Docs

- `docs/HARNESS.md`
- `docs/TRACE_SPEC.md`
- `scripts/README.md`
- `docs/contracts/harness-orchestration-v1.md`

## Acceptance Criteria

- `story verify`, `story verify-all`, and `story complete` start their external
  verification command with `HARNESS_RUN_ID`, `HARNESS_RUN_MODE`, and
  `HARNESS_DB_PATH` removed.
- The CLI's own verification result is still recorded normally after the child
  process exits, including when the parent CLI is running under a orchestrated run.
- Regression tests set all three variables in the parent process and prove that
  a verification command cannot observe them through each supported verification
  entry point.
- The focused test also proves that `verify-all` does not recreate the
  changeset-contamination path that `story verify` already avoids.
- Existing verification success/failure output and status updates remain
  unchanged.

## Design Notes

- Commands: centralize the scrubbed-child-process setup or apply the same
  explicit removals at every verification command launch.
- Queries: none.
- API: CLI only; no new user-facing command.
- Tables: no schema change. Parent-side `story.verify` and completion records
  continue through the normal logged-write path.
- Domain rules: child-process isolation applies only to validation. Intentional
  Harness writes made by the agent or parent CLI retain their run context.
- UI surfaces: terminal output only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Focused Harness CLI tests prove child processes for `verify`, `verify-all`, and completion cannot read the three run-operation-log variables. |
| Integration | Run the focused tests with parent `HARNESS_RUN_ID` set and confirm only the intended parent proof operation is recorded. |
| E2E | A orchestrated run environment can validate a story without fixture operations appearing in its changeset. |
| Platform | `scripts/validate-changeset-rebuild.sh` succeeds after the focused verification run. |
| Release | `cargo fmt --check`, `cargo clippy -p harness-cli -- -D warnings`, and `git diff --check` pass. |

Planned story verification:

```bash
sh -c 'cargo test -p harness-cli validation_subprocesses_do_not_inherit_run_operation_log_env -- --nocapture && scripts/validate-changeset-rebuild.sh && cargo fmt --check && cargo clippy -p harness-cli -- -D warnings && git diff --check'
```

## Harness Delta

Closes the remaining `verify-all` environment-leak path behind backlog item #1
and turns the previous manual changeset-cleanup lesson into executable proof.

## Evidence

Planning evidence: traces 4, 5, and 7 recorded validation fixture writes in
active run changesets. Source inspection confirms `story verify` and the
in-progress `story complete` path scrub the variables, while `story verify-all`
previously launched its child command without doing so.

Implementation adds the same environment removal to `story verify-all` and a
focused regression test that sets all three variables in the parent process,
then proves that `story verify`, `story verify-all`, and `story complete` run
their child command without them. The test also proves the parent CLI still
records `story.verify` and `story.complete` operations. `story verify US-081`
passed, including changeset rebuild, formatting, Clippy, and diff checks.

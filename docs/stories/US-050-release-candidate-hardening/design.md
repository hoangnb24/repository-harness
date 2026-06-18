# Design

## Domain Model

Release hardening adds three operational surfaces:

- `DoctorReport`: required and optional capability checks with redacted
  details.
- `ArtifactAudit`: canonical artifact, package, raw-data, secret, and artifact
  naming validation.
- `demo-full`: make target that orchestrates existing commands for a local
  release-candidate smoke.

These surfaces do not change profiling semantics or artifact contracts.

## Application Flow

1. `make demo-full` runs `vsf-profiler doctor`.
2. It runs the existing `make demo-small`.
3. It runs `vsf-profiler package --input outputs/demo_small --output
   outputs/demo_small_package --zip --force`.
4. It runs `scripts/verify_vsf_artifacts.py` against the run and package.
5. If Node and local Playwright are present, it runs
   `npm run test:e2e:dashboard`; otherwise it prints an explicit skip message.
6. It prints key output paths for the report, package index, manifest, and zip.

## Interface Contract

New CLI command:

```bash
vsf-profiler doctor
```

New audit script:

```bash
python scripts/verify_vsf_artifacts.py \
  --run-dir outputs/demo_small \
  --package-dir outputs/demo_small_package \
  --zip-path outputs/demo_small_package.zip
```

New make target:

```bash
make demo-full
```

## Data Model

No persistent data model changes. The audit script reads existing artifacts and
does not write new product artifacts.

## UI / Platform Impact

No browser UI changes. Playwright remains optional in `make demo-full`; if the
local Node/Playwright toolchain is absent, the target prints a clean skip
message instead of failing.

## Observability

Doctor output names capability status and optional skips without exposing
secret values. The artifact audit prints a concise pass/fail result and
violations with paths and codes.

## Alternatives Considered

1. Add new profiling behavior to make the demo more impressive. Rejected
   because US-050 is release hardening, not feature expansion.
2. Require Playwright and Postgres for `make demo-full`. Rejected because the
   local demo should run on a normal dev machine and clean-skip optional checks.
3. Merge artifact audit into package creation only. Rejected because a standalone
   final audit script is useful for release validation and review.

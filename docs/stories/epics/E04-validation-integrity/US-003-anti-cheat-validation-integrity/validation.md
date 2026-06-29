# Validation

## Proof Strategy

This story is complete when the validation integrity policy exists, protected
surfaces are connected to CODEOWNERS and CI, and the local mechanical check
passes in bootstrap mode.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Static policy snippets exist in Harness docs and templates. |
| Integration | `scripts/validation-integrity-check.py --auto` passes. |
| E2E | Future PR workflow runs the same script. |
| Platform | GitHub Actions workflow is present but not executed locally. |
| Performance | Not applicable. |
| Logs/Audit | Trace records validation-integrity proof and bootstrap exception. |

## Fixtures

- Current bootstrap repository with no baseline commit.
- Placeholder CODEOWNERS owner `@repo-owner`.

## Commands

```text
python3 scripts/validation-integrity-check.py --auto
scripts/bin/harness-cli story verify US-003
scripts/bin/harness-cli story verify-all
scripts/bin/harness-cli audit
git diff --check
```

## Acceptance Evidence

- `python3 scripts/validation-integrity-check.py --auto`
- `scripts/bin/harness-cli tool check --name validation-integrity-check`
- `scripts/bin/harness-cli query tools --capability validation-integrity --status present`
- `scripts/bin/harness-cli decision add --id 0008-validation-integrity-anti-cheat --title "Validation Integrity Anti-Cheat Controls" --doc docs/decisions/0008-validation-integrity-anti-cheat.md`
- `scripts/bin/harness-cli story update --id US-003 --status implemented --unit 1 --integration 1 --e2e 0 --platform 1 --evidence "Validation integrity controls implemented: policy, CODEOWNERS, PR template, CI workflow, mechanical check, decision record, and registered validation-integrity tool."`
- `scripts/bin/harness-cli backlog close --id 3 --status implemented --outcome "Implemented docs/VALIDATION_INTEGRITY.md, CODEOWNERS, PR template, GitHub Actions workflow, validation-integrity check script, decision 0008, and US-003 high-risk story proof."`

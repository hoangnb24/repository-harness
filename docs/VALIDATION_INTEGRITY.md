# Validation Integrity

Validation integrity is the anti-cheat layer for Harness work. The goal is to
keep agents from changing the test, proof, or policy surfaces that judge their
own work without reviewable evidence.

The rule is simple:

```text
agents may propose changes
independent checks produce proof
protected policy changes require reviewable decisions
```

## Threat Model

Agents, humans, or automation can accidentally or intentionally create false
completion by:

- Marking a story implemented without an executable proof command.
- Replacing meaningful tests with trivial tests.
- Weakening assertions, snapshots, fixtures, mocks, or coverage thresholds.
- Editing CI workflows so checks no longer run.
- Editing Harness policy to make the current task look compliant.
- Writing traces or proof flags that are not backed by independent evidence.
- Wrapping the task into a narrower scope after implementation has already
  failed.

## Protected Surfaces

These files define how work is judged and should be treated as protected:

- `AGENTS.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/TEST_MATRIX.md`
- `docs/TRACE_SPEC.md`
- `docs/GIT_WORKFLOW.md`
- `docs/VALIDATION_INTEGRITY.md`
- `docs/templates/`
- `docs/templates/high-risk-story/`
- `.github/CODEOWNERS`
- `.github/pull_request_template.md`
- `.github/workflows/`
- `scripts/validation-integrity-check.py`

Changing a protected surface in normal or high-risk work requires a durable
decision record unless the change is clearly a tiny typo or bootstrap setup.

## Docs Layer

Physical controls:

- Use `.github/CODEOWNERS` so protected docs require owner review.
- Require a durable decision record for policy, source hierarchy, validation,
  branch, trace, or CI workflow changes.
- Keep product truth in `docs/product/*` and story packets, not only in chat.
- Require pull request checkboxes for validation integrity and test changes.
- Fail CI when protected surfaces change without a changed decision file.

Agent rules:

- Do not weaken validation requirements to make a task pass.
- Do not rewrite acceptance criteria after implementation unless the story is
  explicitly changed and the trace names the change.
- Do not treat trace text as a durable decision record.

## Verify Layer

Physical controls:

- Normal and high-risk implemented stories must have a `verify_command`.
- `story verify-all` must run before review or merge.
- CI proof outranks local proof. Local `story verify` is useful but not final
  for shared branches.
- Verification output should name the command, commit SHA, runner, timestamp,
  and artifact or log location when CI exists.
- Missing verification is a blocker unless the story explicitly documents a
  docs-only or bootstrap exception.

Agent rules:

- Do not mark proof flags as passing before the configured command passes.
- Do not replace a strong verify command with a trivial existence check for
  implementation work.
- If a verify command changes, record why in the story and trace.

## Test Layer

Physical controls:

- Any change under test, fixture, snapshot, mock, or coverage paths requires a
  story note explaining whether validation became stronger, equivalent, or
  weaker.
- Weakening validation requires a durable decision record.
- CI should run tests from a clean checkout and should not reuse agent-created
  local artifacts as proof.
- Coverage and mutation testing should be registered when the project stack
  supports them.
- Hidden or reviewer-owned regression tests should be used for security,
  authorization, billing, data loss, and other high-risk behavior.

Validation weakening includes:

- Removing assertions.
- Replacing specific assertions with broad truthy checks.
- Marking tests skipped, ignored, flaky, or expected-to-fail.
- Updating snapshots without explaining the behavior change.
- Mocking the system under test rather than its boundary dependencies.
- Lowering coverage, mutation, lint, typecheck, or E2E thresholds.
- Narrowing fixtures so edge cases disappear.

Agent rules:

- Do not add tests that only prove mocks were called when the contract requires
  behavior proof.
- Do not delete failing tests without explaining whether the product contract
  changed.
- Do not call a test suite sufficient when it does not cover the changed
  contract.

## CI/CD Layer

Physical controls:

- Protect `main`; require pull requests and required status checks.
- Require CODEOWNERS review for protected surfaces.
- Treat CI workflow changes as protected policy changes.
- Pin action versions and run CI with least-privilege permissions.
- Run checks from a clean checkout of the proposed commit.
- Use artifact attestations or provenance when release artifacts matter.
- Keep deploy credentials away from agent-controlled scripts.

Agent rules:

- Do not bypass CI except for an approved hotfix, and record an intervention if
  bypass occurs.
- Do not reduce CI permissions or remove required checks without a decision
  record.

## Trace Layer

Physical controls:

- Trace evidence should reference immutable proof: commit SHA, CI run URL,
  artifact digest, PR number, and story id.
- CI or reviewer records should be separate from agent-written traces.
- Interventions should record human, reviewer, CI, or second-agent corrections.
- Future trace storage should be append-only or remote-backed when the project
  needs tamper resistance.

Agent rules:

- Do not claim success from trace text alone.
- Record skipped checks, narrowed scope, changed tests, and weakened proof in
  `errors`, `harness_friction`, or `notes`.

## Mechanical Check

Run the local integrity check before review:

```bash
python3 scripts/validation-integrity-check.py --auto
```

During repository bootstrap, when no baseline commit exists yet, `--auto`
selects bootstrap behavior. Manual bootstrap mode is also available:

```bash
python3 scripts/validation-integrity-check.py --bootstrap
```

The check validates required anti-cheat files and, after baseline, rejects
protected policy or test/proof changes that lack decision or story evidence.

## References

- SLSA build and provenance requirements: https://slsa.dev/spec/v1.1/requirements
- OWASP CI/CD Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html
- GitHub protected branches and required checks: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- OpenSSF Scorecard checks: https://github.com/ossf/scorecard/blob/main/docs/checks.md
- DeepMind on specification gaming: https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/

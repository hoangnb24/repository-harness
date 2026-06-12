# US-026 Blast-Radius Plugin: Lane-Gated Impact Analysis At Intake

## Status

implemented

## Lane

normal

## Product Contract

When a change request enters intake on the normal or high-risk lane, the agent
runs a blast-radius impact analysis (GitNexus code graph + C3 component model +
durable-layer feature join) whose output gates the risk flags, the validation
re-run set, and the implementation reading list. Tiny-lane work skips it.
Invalid or sparse tooling degrades visibly (UNKNOWN + `Weak proof` flag),
never silently.

## Relevant Product Docs

- `docs/IMPACT_ANALYSIS.md` (policy created by this story)
- `docs/FEATURE_INTAKE.md` (intake hook)
- `docs/HARNESS.md` (task loop this extends)

## Acceptance Criteria

- `docs/IMPACT_ANALYSIS.md` exists and defines: lane-gated trigger, the
  gitnexus/c3 dependency set, preflight validity gates, the file-path join
  pipeline, the coverage signal, and the three gated decisions.
- `docs/FEATURE_INTAKE.md` references the impact analysis step for normal and
  high-risk lanes.
- `gitnexus` and `c3` are registered in this instance's tool registry
  (`harness.db` is local and gitignored by design; the registration commands
  in `docs/IMPACT_ANALYSIS.md` are the per-install seed).
- The empty-join rule is explicit: no feature impact data is reported as
  UNKNOWN with the `Weak proof` flag, never as "no features affected".
- Activation is registry-based: neither tool registered means the plugin is
  inactive and intake skips the step (trace note only, no `Weak proof`);
  registered-but-invalid degrades per the Degraded Modes table.
- Claude-specific dependencies are marked (`claude-skill:` prefix; c3 noted as
  a Claude Code skill in the dependency table).

## Design Notes

- Commands: `harness-cli tool register`, `harness-cli query tools --summary`.
- Queries: agent-side `mcp__gitnexus__impact` / `detect_changes`; c3-audit.
- Tables: no schema changes; reuses `tool`, `trace.files_changed`,
  `trace.story_id`, `story.contract_doc`.
- Domain rules: agent-orchestrated, harness-recorded; degrade-don't-lie;
  no curated feature-to-component mapping artifact.
- Deliberately excluded until friction recorded: hard CLI enforcement of
  `story_id`/`contract_doc`, new DB tables, CI gates, installer flag.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Verify command: policy doc exists and intake hook references it. |
| Integration | Tool registry rows present (`query tools --summary`). |
| E2E | Not applicable (docs/process module; no app surface). |
| Platform | Not applicable. |
| Release | Not applicable. |

## Harness Delta

- New policy doc `docs/IMPACT_ANALYSIS.md`.
- `docs/FEATURE_INTAKE.md` gains an impact analysis step for normal/high-risk.
- Tool registry rows for `gitnexus` and `c3`.
- Backlog #1 records the originating friction and predicted impact.
- Follow-up: activation/skip ladder and Claude-specific tool marking added to
  `docs/IMPACT_ANALYSIS.md` (intake #2); Backlog #3 proposes
  `harness-cli impact preflight` for mechanical mode detection.

## Evidence

- `scripts/bin/harness-cli story verify US-026` (doc + hook check).
- `scripts/bin/harness-cli query tools --summary` shows gitnexus and c3.

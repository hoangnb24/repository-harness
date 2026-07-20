# 0006 Phase 4 Benchmark Triage

Date: 2026-05-31

## Status

Accepted for the legacy benchmark and CLI contract. Mandatory default-path
recording rules are superseded by
`0019-repository-centered-default-workflow.md`.

## Context

The first Phase 4 benchmark re-run found that T4 authentication failed
`decision_recorded` even though the trace included decisions text. The same run
also showed command churn from agents trying `story update` proof flags with
`yes` and `no`, and trying to use `story verify` as if it accepted proof flags.

## Decision

Harness instructions and CLI help must distinguish durable records from trace
evidence and must show the current Rust CLI command shape at the point agents
need it:

- High-risk behavior changes require a markdown decision under
  `docs/decisions/` and a durable `decision` row.
- Trace `--decisions` is evidence for trace quality, not the decision log.
- `story update` proof flags use `1` and `0`.
- `story verify <id>` only runs the configured `verify_command`; proof flags
  stay on `story update`.

## Alternatives Considered

1. Rely on trace auto-scoring to catch the missing T4 decision. Rejected because
   trace scoring can confirm detailed trace content but cannot prove a durable
   decision record exists.
2. Change the CLI to accept `yes` and `no`. Deferred because v0.1.5 already has
   a numeric command contract and the immediate benchmark issue is stale
   guidance, not missing parser capability.

## Consequences

Positive:

- High-risk agents get explicit decision-log instructions before closing work.
- Command examples align with the Rust CLI v0.1.5 parser.
- `story verify` and `story update` have separate mental models in docs.

Tradeoffs:

- Docs now duplicate a few command examples so the common path is visible
  without repeated help discovery.

## Follow-Up

- Re-run the Phase 4 benchmark and check whether T4 records a durable decision.
- Watch for remaining command churn around `story update` and `story verify`.

# Decisions

Decision records preserve lasting product, architecture, compatibility,
security, data-ownership, and validation choices.

Decision records are optional locations chosen by the user or consumer workflow.
Existing accepted decisions retain their authority; `docs/templates/decision.md`
is an available reference, not a required task step.

## Current Upstream Decisions

| Decision | Title |
| --- | --- |
| 0019 | Repository Authority (workflow provisions historical) |
| 0020 | Installation Profiles And Knowledge Boundaries |
| 0024 | Rust Harness Core Maintenance CLI |
| 0025 | Latest-Release Self-Update And Human-Directed Conflicts |
| 0026 | Explicit Onboarding Skills In Default Core |
| 0027 | End Protocol V1 And Focus The Repository Protocol |
| 0028 | Authoritative Invariant Encoding |
| 0029 | Measured Skills, Context Budget, And Approval Frontmatter (proposed) |

These decisions describe upstream Harness. Installed consumers begin with an
empty decision index and add only real consumer choices.

## History

Superseded database lifecycle, story, trace, orchestration, and migration
decisions remain available through Git history. They are absent from the
current index so agents do not confuse historical authority with current
product behavior.

## Retaining Rationale

Preserve accepted intent and consequential rationale that code and tests cannot
express. Link to implementation knowledge rather than duplicating it. The
consumer owns when to create or retain a record.

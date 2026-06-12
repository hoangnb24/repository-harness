# Impact Analysis

Blast-radius analysis for change requests. It answers, with evidence instead of
judgment: which components (technical perspective) and which features (product
perspective) a change touches, how they are touched, and what proof must re-run.

The harness records and gates; the agent orchestrates. The two analysis tools
are agent-side (an MCP server and a skill), so no `harness-cli` subcommand runs
them. The CLI holds the tool registry, the durable evidence the feature join
depends on, and the trace where results are stamped.

## When It Runs

Impact analysis is lane-gated. Context spend stays proportional to risk.

| Lane | Impact analysis |
| --- | --- |
| Tiny | Skip. The risk checklist alone is enough. |
| Normal | Must run before the risk checklist is completed. |
| High-risk | Must run, and its output is required evidence in the story packet. |

Also run it, regardless of provisional lane, when the agent cannot confidently
name the affected files, components, or product docs from the request alone.
If the result escalates the lane, re-enter intake with the new lane.

## Dependencies

| Tool | Provides | Form | Agent runtime |
| --- | --- | --- | --- |
| GitNexus | Code graph: changed files, dependents, call paths | MCP server (`mcp__gitnexus__impact`, `detect_changes`) | Any MCP-capable agent |
| C3 | Named component model with declared code locations | `.c3/` docs plus the `c3` skill (`c3-audit` for drift) | Claude Code skill (Claude-specific) |

Registering a tool is the plugin activation switch (see Activation And Skip
Rule). Use the `mcp:` prefix for MCP servers and `claude-skill:` for
Claude-specific skills so non-Claude agents can tell which dependencies they
can orchestrate:

```bash
scripts/bin/harness-cli tool register --force --name gitnexus --command "mcp:gitnexus" \
  --description "Code-graph blast radius" --responsibility Verification
scripts/bin/harness-cli tool register --force --name c3 --command "claude-skill:c3" \
  --description "Component model and drift audit (Claude Code skill)" --responsibility Verification
```

## Activation And Skip Rule

Impact analysis is a harness plugin. Registration in the tool registry is the
activation switch, and it separates a legitimate skip from a failed gate:

- Neither `gitnexus` nor `c3` is registered: the plugin is inactive. Skip
  impact analysis entirely; intake proceeds with the baseline risk checklist.
  Note `impact: skipped, plugin inactive` in the trace. Skipping an inactive
  plugin is not drift and does not set the `Weak proof` flag.
- A tool is registered but missing, stale, or drifted: the repo declared
  intent to rely on it, so this is a failed validity gate, not a skip.
  Degrade per Degraded Modes and set the `Weak proof` flag.

## Degraded Modes

| Mode | Available | Blast radius | Components | Features | Posture |
| --- | --- | --- | --- | --- | --- |
| Full | gitnexus + c3 | changed files + dependents | C3 names | trace join + coverage | Normal operation. |
| Partial | one of the two | git-diff files only when gitnexus is absent | raw file paths when c3 is absent | trace join, lower coverage | Set `Weak proof`. |
| Inactive | neither registered | not computed | not computed | not computed | Skip; trace note only. |

## Preflight Validity Gates

Run before every impact query. Invalid tooling must degrade visibly, never
produce silently stale results.

| Dependency | Validity check | On failure |
| --- | --- | --- |
| GitNexus | Index in sync with HEAD (`detect_changes`, re-index if behind) | Component impact reported as UNKNOWN, not empty. |
| C3 | `.c3/` exists and `c3-audit` is clean since the last structural change | Degrade component names to raw file paths; feature join still runs. |

Any failed gate sets the `Weak proof` risk flag on the intake row and is noted
in the trace.

## Pipeline

```text
change request
  -> gitnexus impact: changed files + dependent files (blast radius)
       -> map files to C3 components via declared code locations
       -> join files against trace history (trace.files_changed)
            -> story (trace.story_id)
            -> product doc (story.contract_doc)
  -> impact set: components + features + coverage
```

The join key is file paths. No curated feature-to-component mapping exists or
should be created; the durable layer accumulates the feature edge as a side
effect of normal trace discipline.

## Coverage Signal

An empty feature join has two indistinguishable causes: no impact, or no data.
Never report it as empty. Every impact result states coverage:

```text
coverage: N of M blast-radius files have story/trace history
```

When coverage is below half, report feature impact as UNKNOWN, set the
`Weak proof` risk flag, and fall back to reading the relevant `docs/product/*`
manually. Feature-impact quality is emergent: it is weak in a fresh install and
improves only while traces carry `--story` and stories carry `--contract`
(the `story.contract_doc` column).

## Gated Decisions

The impact set exists to change decisions, not to be context. It must feed:

1. Risk flags: `Existing behavior`, `Multi-domain`, and `Public contracts` are
   answered from the impact set, not judgment.
2. Validation scope: stories in the impact set form the required re-run set;
   run `scripts/bin/harness-cli story verify <id>` once per story in the set.
3. Reading list: the affected product docs and components become the
   implementation-phase reading list.

Record the impact summary, coverage, and any failed validity gate in the trace
notes for the task. If the analysis was skipped where this document requires
it, say so in the trace rather than implying it ran.

# Tool Registry

The harness deals with two distinct kinds of "tool". Keep them separate.

| | Capability manifest (outbound) | Inbound tool registry |
| --- | --- | --- |
| Direction | harness offers it to the agent | a project equips it for the harness to use |
| Examples | the `harness-cli` subcommands below | gitnexus, c3, a linter, a deploy check |
| Presence | always compiled in | optional; may be absent on any machine |
| If missing | n/a (it is the harness) | clean skip; never blocks the main process |

This document describes both. The **inbound registry** is the extension base:
it is where the harness learns what extra capability is equipped, what purpose
it serves, and whether it is actually present right now, so a workflow step can
adapt to what is installed without the core ever depending on it.

## Inbound Registry: Register A Tool

```bash
scripts/bin/harness-cli tool register \
  --name deploy-check \
  --kind cli \
  --capability deploy-verification \
  --command ./scripts/deploy-check.sh \
  --description "Verify deploy health before release" \
  --responsibility Verification \
  --args "env:enum:required:staging,production"
```

Fields specific to inbound tools:

- `--kind` — how the tool is reached and probed. One of `cli`, `binary`, `mcp`,
  `skill`, `http`. Defaults to `cli`. The kind tells each agent runtime what it
  can orchestrate (a non-Claude agent simply treats a `skill` it cannot run as
  absent) and tells `tool check` which probe to use.
- `--capability` — the workflow purpose a step looks the tool up by. Free-text
  but normalized to kebab-case, so `Impact Analysis`, `impact_analysis`, and
  `impact-analysis` all register as `impact-analysis`. This is the only coupling
  between a step and a tool; steps reference the capability, never the tool name.
- `--scan` — for `mcp`/`skill`/`http`, a declarative path or URL that
  `tool check` resolves to decide presence (e.g. `.c3`, `~/.claude/skills/c3`,
  `https://localhost:8080/health`). `cli`/`binary` are probed via their command.

`--force` is only needed for `cli`/`binary` whose command is intentionally
absent on the current machine. `mcp`/`skill`/`http` are not on `PATH` by nature,
so they register without `--force`; their presence is resolved later by
`tool check`.

Registering an MCP server or a Claude skill (examples):

```bash
scripts/bin/harness-cli tool register --name gitnexus --kind mcp \
  --capability impact-analysis --scan ".gitnexus" --command "mcp:gitnexus" \
  --description "Code-graph blast radius" --responsibility Verification
scripts/bin/harness-cli tool register --name c3 --kind skill \
  --capability impact-analysis --scan ".c3" --command "skill:c3" \
  --description "Component model and drift audit (Claude skill)" \
  --responsibility Verification
```

Remove a tool with:

```bash
scripts/bin/harness-cli tool remove --name deploy-check
```

## Inbound Registry: Check Presence

Registration records intent. `tool check` reconciles intent with reality by
scanning each registered tool and persisting the verdict (`status` and
`checked_at`). Run it at intake start so status reflects current reality.

```bash
scripts/bin/harness-cli tool check            # scan all registered tools
scripts/bin/harness-cli tool check --name c3  # scan one
scripts/bin/harness-cli tool check --json     # machine-readable for agents
```

Probe per kind:

| Kind | Probe | `present` means |
| --- | --- | --- |
| `cli`, `binary` | command resolves on `PATH` or as a path | installed and runnable |
| `mcp`, `skill` | `scan_target` path resolves (`~` expands) | equipped/configured on disk |
| `http` | `scan_target` reachable over TCP (2s), else path | endpoint answers |

`tool check` always exits `0`: a missing extension is a fact to report, not a
CLI failure. A `cli`/`binary` is `present` when runnable. An `mcp`/`skill`/`http`
`present` means **equipped** (config/file resolves), not **live this session** —
the agent still confirms live usability at call time, since only the agent
runtime can see whether its MCP server is actually connected. With no
`scan_target`, the status is `unknown` and the agent must confirm.

## Inbound Registry: Look Up By Capability

A workflow step asks "what is present for this purpose?" rather than naming a
tool:

```bash
scripts/bin/harness-cli query tools --capability impact-analysis
scripts/bin/harness-cli query tools --capability impact-analysis --status present
```

The result is the set of providers. Multiple tools may provide one capability
(gitnexus and c3 both serve `impact-analysis` and are complementary), so a step
reads the set and degrades on how much of it is present.

### Degrade Ladder

The CLI reports facts (`status`); the agent applies policy. The generic rule,
keyed on the present-provider count for a capability:

| Providers present | Posture | Agent behavior |
| --- | --- | --- |
| none registered | Inactive | clean skip; note `capability X: inactive` in the trace. Not drift. |
| registered but none/some present | Degraded | run with what resolves; set the `Weak proof` flag; note the gap. |
| all present | Full | normal operation. |

A registered tool that scans as `missing` is a failed validity gate, not a skip.
A capability with no registered providers is simply inactive and is skipped
without penalty — this is what keeps the core seamless on a fresh install.

### Recommended Capability Vocabulary

Capability is open (no code change to add one), but a step and its providers
must agree on the exact string. Reuse these where they fit before coining a new
one; coin new ones in kebab-case:

```
impact-analysis · deploy-verification · coverage · security-scan
performance-benchmark · documentation-lookup
```

## Inspecting The Registry

```bash
scripts/bin/harness-cli query tools --summary
scripts/bin/harness-cli query tools --json
scripts/bin/harness-cli query tools --responsibility Verification
```

JSON records carry `kind`, `capability`, `scan_target`, `status`, and
`checked_at` alongside the existing fields, so any agent can read the registry
without parsing the human table.

## Compiled Harness Commands (Outbound Manifest)

| Command | Responsibility | Purpose | Arguments |
| --- | --- | --- | --- |
| `init` | Task state | Create the harness database. | none |
| `migrate` | Task state | Apply pending schema migrations. | none |
| `import brownfield` | Project memory | Seed durable records from markdown state. | none |
| `intake` | Task specification | Record a feature intake classification. | `--type`, `--summary`, `--lane` |
| `story add` | Task state | Create a durable story record. | `--id`, `--title`, `--lane`, optional `--verify` |
| `story update` | Task state | Update story status, proof flags, evidence, or verification command. | `--id`, optional proof/status fields |
| `story dependency add` | Task state | Add a cycle-safe durable dependency edge. | `--blocker`, `--blocked` |
| `story dependency remove` | Task state | Remove a durable dependency edge; missing edges are unchanged. | `--blocker`, `--blocked` |
| `story backlog link` | Task state | Add a replayable `resolves` or `references` link to a stable backlog occurrence. | `--story`, `--backlog`, `--relationship` |
| `story backlog unlink` | Task state | Remove a relationship; closed resolver provenance remains immutable. | `--story`, `--backlog` |
| `story backlog list` | Task state | Show story-to-backlog relationships. | optional `--story`, `--backlog` |
| `story verify` | Verification | Run one story `verify_command` and record pass/fail. | story id |
| `story complete` | Task state | Run fresh proof and atomically implement an eligible story plus accepted resolver backlog work. | story id |
| `story verify-all` | Verification | Run all configured story verification commands and skip stories without one. | none |
| `decision add` | Project memory | Create a durable decision record. | `--id`, `--title`, optional `--doc`, `--verify` |
| `decision verify` | Verification | Run one decision verification command. | decision id |
| `backlog add` | Entropy auditing | Record a harness improvement proposal. | `--title`, optional pain/suggestion/risk/predicted fields |
| `backlog close` | Entropy auditing | Close a backlog item with outcome evidence. | `--id`, optional `--status`, `--outcome` |
| `tool register` | Tool access | Register an external project tool. | `--name`, `--command`, `--description`, `--responsibility`, optional `--kind`, `--capability`, `--scan`, `--args`, `--force` |
| `tool check` | Tool access | Scan registered tools and persist present/missing/unknown status. | optional `--name`, `--json` |
| `tool remove` | Tool access | Remove a registered external tool. | `--name` |
| `intervention add` | Intervention recording | Record a human, reviewer, CI, or agent intervention. | `--type`, `--description`, `--source`, optional `--trace`, `--story`, `--impact` |
| `trace` | Observability | Record an agent execution trace and print trace quality. | `--summary`, optional trace fields |
| `score-trace` | Observability | Score trace detail against lane requirements. | optional `--id` |
| `score-context` | Context selection | Score trace reads against compiled context rules. | trace id |
| `audit` | Entropy auditing | Run drift checks and compute entropy score. | none |
| `propose` | Entropy auditing | Read deterministic improvement proposals, or explicitly accept/reject one stable key. | `--accept <key>` plus one outcome schedule, or `--reject <key> --reason <text>` |
| `query matrix` | Task state | Show durable story proof matrix. | optional `--numeric` |
| `query dependencies` | Task state | Show story dependency edges. | optional `--story` |
| `query backlog` | Entropy auditing | Show Harness improvement backlog and, with `--id`, its relationships. | optional `--open`, `--closed`, `--id` |
| `query decisions` | Project memory | Show durable decision records. | none |
| `query intakes` | Task specification | Show recent intake records. | none |
| `query traces` | Observability | Show recent trace records. | none |
| `query friction` | Failure attribution | Show traces with harness friction. | none |
| `query tools` | Tool access | Show compiled and registered tool entries. | optional `--json`, `--summary`, `--responsibility`, `--capability`, `--status` |
| `query interventions` | Intervention recording | Show intervention records. | optional `--trace`, `--story`, `--type` |
| `query stats` | Task state | Show durable record counts. | none |
| `query sql` | Tool access | Run arbitrary SQL against `harness.db`. | SQL text |
| `db changeset apply` | Task state | Apply one semantic changeset idempotently. | changeset path |
| `db rebuild` | Task state | Rebuild a fresh `harness.db` from semantic changesets. | `--from` changeset directory |

## Validation Rules

- Tool names must be unique among registered tools.
- Descriptions must be 10-200 characters.
- Responsibilities must match the Runtime Substrate responsibility list.
- `--kind` must be one of `cli`, `binary`, `mcp`, `skill`, `http`.
- `--capability` must be kebab-case (lowercase letters, digits, single hyphens);
  spaces and underscores are normalized to hyphens.
- `--args` entries must use `name:type:required` or
  `name:type:required:help`, with `required` or `optional` as the third field.
- For `cli`/`binary`, the command must exist as a path or on `PATH`, unless
  `--force` is supplied. `mcp`/`skill`/`http` skip this check.

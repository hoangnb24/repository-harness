# Repository Agent Map

This map points an agent to the target repository's own sources. Replace every
angle-bracket marker before activating the map. Keep each route bounded: link
the smallest source that answers the question, then let that source name any
deeper context.

## Authority

- Repository instructions: `<path or unavailable>`
- Product or behavior contract: `<path or unavailable>`
- Ownership and approval rules: `<path or unavailable>`
- Local overrides: `<path and scope or none>`

When sources conflict, stop at the conflict, preserve target-owned content,
and ask the named owner. Do not infer permission from the presence of this
template.

## Bounded Routes

| Need | Read or run first | Continue only when | Stop when |
| --- | --- | --- | --- |
| Plan work | `<planning triggers and current plans>` | The target requires a plan or an existing plan names the next source. | The planning mode, scope, and exact next action are known. |
| Understand architecture | `<architecture map or boundary document>` | The selected change crosses a named boundary or the map links a narrower source. | Affected owners, interfaces, and invariants are known. |
| Validate a change | `<validation ladder or command index>` | A failed step points to a narrower check or remediation source. | Required checks pass or a concrete blocker is recorded. |
| Obtain feedback | `<tests/build/review/runtime/docs/deploy/recovery route>` | The task touches that surface and the route is available. | Direct target feedback is captured; unavailable routes are recorded as unavailable. |
| Maintain the repository | `<maintenance/gardening contract>` | A named trigger or cadence is due and the bounded scope applies. | The convergence check passes or the owner accepts a recorded exception. |

## Planning Triggers

- No plan: `<bounded change conditions>`
- Lightweight plan: `<conditions and target-owned location>`
- Resumable plan: `<conditions and target-owned location>`

A plan exists to preserve work state when the target needs it. Do not create a
plan solely to satisfy an external tool.

## Validation Ladder

Run the smallest relevant step first and stop on the first failure.

| Order | Target-owned check | Applies when | Expected result | Failure route |
| --- | --- | --- | --- | --- |
| 1 | `<fast local check>` | `<condition>` | `<result>` | `<path or owner>` |
| 2 | `<focused behavior check>` | `<condition>` | `<result>` | `<path or owner>` |
| 3 | `<broader repository check>` | `<condition>` | `<result>` | `<path or owner>` |
| 4 | `<platform or release check>` | `<condition>` | `<result>` | `<path or owner>` |

## Target-Owned Capability Contracts

### Invariants

| Invariant | Owner | Check | Remediation | Exception path |
| --- | --- | --- | --- | --- |
| `<rule>` | `<target owner>` | `<command or inspection>` | `<bounded repair>` | `<approval path or none>` |

### Feedback

| Surface | Owner | Direct route | Success signal | Unavailable behavior |
| --- | --- | --- | --- | --- |
| `<surface>` | `<target owner>` | `<command, path, or interface>` | `<observable result>` | `<record unavailable and use named fallback>` |

### Repeated Corrections

When the same correction recurs, the target owner chooses the durable home:
instruction, example, test, check, script, review rule, or another
repository-native capability. Record the trigger, owning path, discovery route,
validation, and retirement rule. Conversation history alone is not durable
capability.

### Gardening

| Scope | Owner | Trigger or cadence | Runner | Bounded change policy | Validation | Convergence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<paths or concern>` | `<target owner>` | `<event or interval>` | `<person or automation>` | `<allowed edits and exclusions>` | `<check>` | `<second equivalent run finds no repeat drift>` |

## Resume Capsule

- Objective: `<current outcome>`
- Completed: `<verified work>`
- Remaining: `<bounded work>`
- Exact next action: `<one command, inspection, or edit with its target>`
- Validation ladder: `<ordered target-owned checks and stop-on-failure rule>`
- Decisions and assumptions: `<paths or concise list>`
- Blockers and owners: `<blocker -> owner, or none>`
- Working state: `<revision, changed paths, and required environment facts>`

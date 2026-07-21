#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
fixture="$temp/task-tracker"
mkdir -p "$fixture/docs/product" "$fixture/docs/plans/active" \
  "$fixture/docs/plans/completed" "$fixture/src" "$fixture/tests"

cat >"$fixture/docs/product/tasks.md" <<'EOF'
# Task Status

A task is overdue only when its due date has passed and its status is neither
done nor canceled.
EOF

cat >"$fixture/src/task-status.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
status=$1
due=$2
if [[ "$due" == past && "$status" != done ]]; then
  echo overdue
else
  echo not-overdue
fi
EOF
chmod +x "$fixture/src/task-status.sh"

fingerprint() {
  find "$fixture" -type f -print0 | LC_ALL=C sort -z |
    xargs -0 shasum -a 256 | shasum -a 256 | awk '{print $1}'
}

assert_no_control_plane_state() {
  [[ ! -e "$fixture/harness.db" ]]
  [[ ! -e "$fixture/.harness" ]]
}

# Read-only task: inspect the product rule and existing visible behavior. The
# complete fixture fingerprint must remain unchanged.
before_read=$(fingerprint)
grep -Fq 'done nor canceled' "$fixture/docs/product/tasks.md"
[[ "$("$fixture/src/task-status.sh" done past)" == not-overdue ]]
[[ "$before_read" == "$(fingerprint)" ]]
assert_no_control_plane_state

# Bounded documentation task: clarify a display rule directly beside the
# authoritative product behavior; no plan or control-plane record is created.
cat >>"$fixture/docs/product/tasks.md" <<'EOF'

The task list displays overdue state as a label, not as a new task status.
EOF
grep -Fq 'not as a new task status' "$fixture/docs/product/tasks.md"
[[ -z "$(find "$fixture/docs/plans/active" -type f -print -quit)" ]]
assert_no_control_plane_state

# Bounded code and user-visible task: first reproduce the canceled-task bug at
# the executable boundary, then fix it and add regression proof.
[[ "$("$fixture/src/task-status.sh" canceled past)" == overdue ]]
cat >"$fixture/src/task-status.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
status=$1
due=$2
if [[ "$due" == past && "$status" != done && "$status" != canceled ]]; then
  echo overdue
else
  echo not-overdue
fi
EOF
chmod +x "$fixture/src/task-status.sh"
cat >"$fixture/tests/test-task-status.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
app=$1
[[ "$("$app" todo past)" == overdue ]]
[[ "$("$app" done past)" == not-overdue ]]
[[ "$("$app" canceled past)" == not-overdue ]]
EOF
chmod +x "$fixture/tests/test-task-status.sh"
"$fixture/tests/test-task-status.sh" "$fixture/src/task-status.sh"
[[ "$("$fixture/src/task-status.sh" canceled past)" == not-overdue ]]
assert_no_control_plane_state

# Durable task: two explicit checkpoints update one Git-native plan before the
# verified plan moves to completed history. No parallel story or trace exists.
plan="$fixture/docs/plans/active/team-time-zones.md"
cat >"$plan" <<'EOF'
# Execution Plan: Team Time Zones

## Status
Active
## Outcome
Use team-local dates at the task boundary.
## Context
Task status contract and executable status surface.
## Scope
Status calculation only.
## Approach
First contract, then implementation.
## Risks And Recovery
Keep the old calculation recoverable in Git.
## Progress
- [x] Checkpoint 1: product boundary inspected.
- [ ] Checkpoint 2: focused proof recorded.
## Decisions
- Keep task status values unchanged.
## Validation
- Focused proof: pending.
## Result
Pending.
EOF
grep -Fq 'Checkpoint 1' "$plan"
sed -i.bak \
  -e 's/\[ \] Checkpoint 2/\[x\] Checkpoint 2/' \
  -e 's/Focused proof: pending/Focused proof: tests\/test-task-status.sh passed/' \
  -e 's/Pending\./Verified in the executable task-status fixture./' "$plan"
rm "$plan.bak"
grep -Fq '[x] Checkpoint 2' "$plan"
grep -Fq 'tests/test-task-status.sh passed' "$plan"
mv "$plan" "$fixture/docs/plans/completed/team-time-zones.md"
[[ ! -e "$plan" ]]
[[ -f "$fixture/docs/plans/completed/team-time-zones.md" ]]
assert_no_control_plane_state

# Judgment task: “simplify task permissions” has two product-significant
# meanings in the canonical demo. Inspection identifies the ambiguity and the
# application remains untouched while direction is absent.
before_judgment=$(shasum -a 256 "$fixture/src/task-status.sh" | awk '{print $1}')
grep -Fq 'allow every teammate to edit every task' "$root/docs/demo/README.md"
grep -Fq 'keep ownership restrictions but simplify the permission code' \
  "$root/docs/demo/README.md"
grep -Fq '`Add rate limiting` without a quota' "$root/docs/WORKFLOW.md"
grep -Fq 'must stop' "$root/docs/WORKFLOW.md"
grep -Fq 'configurable defaults are not authority' "$root/AGENTS.md"
after_judgment=$(shasum -a 256 "$fixture/src/task-status.sh" | awk '{print $1}')
[[ "$before_judgment" == "$after_judgment" ]]
assert_no_control_plane_state

# Fixed acceptance comparison. The former mandatory entry path was AGENTS.md,
# feature intake, and context rules (2,413 words at the Phase 1 baseline). The
# new mandatory map plus workflow is bounded to 1,000 words and uses zero
# Harness commands for every bounded scenario above.
entry_words=$(awk '{ words += NF } END { print words }' \
  "$root/AGENTS.md" "$root/docs/WORKFLOW.md")
[[ "$entry_words" -le 1000 ]]
[[ "$entry_words" -lt 2413 ]]

echo "repository workflow scenarios passed: harness_commands=0 entry_words=$entry_words baseline_words=2413 interventions=1/1 ambiguous tasks"

# Repository-Centered Workflow Demo

This walkthrough shows how the same repository handles four different requests
without forcing them through one lifecycle.

Assume a small team task tracker with this product rule in
`docs/product/tasks.md`:

```text
A task has a title, status, assignee, and optional due date.
Supported statuses are todo, in_progress, done, and canceled.
Only an unfinished task whose due date has passed is overdue.
```

## 1. Read-Only Question

Request:

```text
When does a task become overdue?
```

Step by step:

1. Read `AGENTS.md`, which points to the repository map.
2. Open the relevant product contract, `docs/product/tasks.md`.
3. Answer from that rule and cite the file.
4. Do not bootstrap a database, create an intake, write a trace, or modify the
   repository.

Cause and effect: the question needs evidence, not durable workflow state. A
read-only path makes the answer faster and prevents an explanation from
silently mutating the project.

## 2. Bounded Change

Request:

```text
Fix the task list so canceled tasks are not marked overdue.
```

Step by step:

1. Read the overdue rule and locate the task-list calculation.
2. Inspect the nearest tests and repository validation command.
3. Keep a short working plan in the current session.
4. Change the calculation to require an unfinished, non-canceled task.
5. Add or update a regression test for a canceled task with a past due date.
6. Run the focused test, then the repository's relevant validation gate.
7. Report the changed behavior and proof.

Cause and effect: the scope is local and recoverable from the diff. Creating a
durable plan or database row would add synchronization work without preserving
information that Git and the test do not already contain.

## 3. Durable Change

Request:

```text
Replace local due-date handling with team time zones across the API, worker,
UI, and stored data.
```

Step by step:

1. Inspect the product, architecture, migration, and validation surfaces.
2. Copy `docs/templates/exec-plan.md` to a descriptive file under
   `docs/plans/active/`.
3. Record the goal, non-goals, affected boundaries, phases, risks, rollback,
   and proof commands.
4. Commit the plan so another session can resume from repository state alone.
5. Implement in reviewable groups. After each group, update progress and
   validation evidence in the plan and commit both the work and its durable
   memory.
6. Record a decision under `docs/decisions/` if the time-zone model is an
   architectural choice future work must inherit.
7. Run end-to-end proof across the visible application boundary.
8. Mark the plan complete and move it to `docs/plans/completed/`.

Cause and effect: this change spans boundaries and may outlive one session. A
versioned plan prevents chat history from becoming the only record of sequence,
tradeoffs, recovery, and remaining work.

## 4. Consequential Ambiguity

Request:

```text
Simplify task permissions.
```

The repository reveals at least two plausible interpretations:

- allow every teammate to edit every task; or
- keep ownership restrictions but simplify the permission code.

Step by step:

1. Inspect the current permission contract and callers.
2. Identify that one interpretation changes who may modify user data.
3. Pause before editing code.
4. Present the two choices with concrete effects: access expansion versus an
   implementation-only refactor.
5. Continue only when the requested product behavior is authoritative.

Cause and effect: uncertainty is not solved by adding more process records. It
is solved by keeping a consequential product decision with the human who owns
it.

## What Is Deliberately Absent

None of these default flows requires a story row, proof matrix, trace score,
audit record, proposal, or local SQLite database. Those remain available as a
compatibility control plane when an external orchestrator explicitly needs
them; they do not sit between a normal request and repository work.

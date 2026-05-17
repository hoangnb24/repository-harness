# Harness Backlog

Use this file when an agent discovers a missing harness capability but should
not change the operating model immediately.

## Template

```md
## Missing Harness Capability

### Title

Short name.

### Discovered While

Task or story that exposed the gap.

### Current Pain

What was hard, repeated, ambiguous, or unsafe?

### Suggested Improvement

What should be added or changed?

### Risk

Tiny, normal, or high-risk.

### Status

proposed | accepted | implemented | rejected
```

## Items

## Missing Harness Capability

### Title

Bootstrap mode for `install-harness.sh`

### Discovered While

Documenting greenfield workflow from `SPEC.md` (2026-05-17).

### Current Pain

`install-harness.sh` assumes the target directory is an existing project
(prompts to merge / override / stop on existing files). Greenfield
projects starting from a written spec require manual steps:
`git clone` the harness, `rm -rf .git && git init`, manually place
`SPEC.md`. The README's "Greenfield Bootstrap" section now documents
this manual path, but it should be a single command.

### Suggested Improvement

Add a `--bootstrap` flag that:
1. Initializes a fresh git repo in the target directory.
2. Copies all harness files unconditionally (no merge prompts).
3. Optionally accepts `--spec <path>` to copy the user's spec to
   `./SPEC.md` in one step.
4. Prints the "next prompt" (the Claude Code prompt that runs Phase 1
   intake) so the user can copy-paste straight in.

### Risk

Normal.

### Status

proposed


# Exec Plan

## Goal

Reframe VSF Data Profiler as a generic CSV plus DBML/schema Smart EDA tool
without breaking existing artifact names, CLI behavior, or optional advanced
features.

## Scope

In scope:

- README, product, architecture, demo, and release wording.
- Generated Markdown/HTML report templates.
- Offline package `index.html` copy.
- Local web runner visible copy.
- Optional L4 prompt and deterministic narrative wording.
- Tests that assert user-facing strings.

Out of scope:

- Artifact renames.
- Connector, PDF, package, benchmark, or dashboard feature removal.
- New MySQL/PDF implementation.

## Risk Classification

Risk flags:

- Public contracts: report/web/package/L4 copy is user-visible.
- Existing behavior: tests assert current generated output strings.
- Multi-domain: docs, templates, web, L4, and package surfaces change.
- Weak proof: some copy risk is caught by scans rather than single-purpose
  assertions.

Hard gates:

- External provider behavior, because the OpenAI prompt task wording changes.

## Work Phases

1. Discovery.
2. Design.
3. Validation planning.
4. Implementation.
5. Verification.
6. Harness update.

## Stop Conditions

Pause for human confirmation if:

- Artifact names or JSON keys need to change.
- Validation requirements need to be weakened.
- Optional advanced features would need to be removed rather than reframed.

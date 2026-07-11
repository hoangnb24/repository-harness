# Design

## Timestamp Contract

All version 2 SQLite lifecycle timestamps use exact `YYYY-MM-DD HH:MM:SS`.
Shared helpers parse and round-trip required and optional values. Version 1
fallback-to-now behavior remains for replay compatibility.

Covered families: story/backlog completion, verification, proposal decisions
and evidence, outcome observations, interventions, traces, and audit episodes.

## List Contract

Ordinary text remains comma-separated. Input beginning with `[` or `{` is
treated as JSON intent: only an array of strings is accepted; mixed, object, or
malformed input returns a typed CLI error.

## Validator Tests

Binary selection becomes a small injectable function. SQL proof validation is
callable against fixture databases, while operation parser tests cover bad
changesets separately.

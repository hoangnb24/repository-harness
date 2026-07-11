# Exec Plan

1. Register US-085 after US-084.
2. Add canonical timestamp helpers and table-driven operation tests.
3. Add typed JSON-like list parsing at CLI boundaries.
4. Refactor validator helpers and shell fixtures for causal coverage.
5. Run workspace/rebuild proof, record detailed trace, complete story, close ledger.

High-risk gates: no history deletion, no v1 compatibility break, and no
validator claim without a test that reaches the named branch.

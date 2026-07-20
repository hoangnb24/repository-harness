# Execution Plan

1. Add compare-and-swap replacement flags to snapshot publication.
2. Test successful replacement, stale-precondition refusal, unchanged tuple on
   refusal, verification, and materialization from the replacement.
3. Bootstrap tracked state before Linux and Windows CI validation.
4. Add a workflow contract test that preserves ordering and fresh-state checks.
5. Run a final disposable materialization, all E15 fixtures, and the full
   pre-merge suite.
6. Close US-119, mark E15 complete, and record the final detailed trace.

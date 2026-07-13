# Design

## Domain Model

The central invariant is:

```text
implemented story
  -> fresh configured verification passed
  -> explicit completion transaction committed
```

Generic status mutation may select lifecycle states used to prepare work, but
must reject `implemented`. Historical import and semantic replay remain trusted
reconstruction paths and do not become interactive bypasses.

A query is defined by effect, not command spelling: its SQLite connection must
reject writes even if SQL parsing, CTEs, pragmas, or `RETURNING` clauses disguise
the statement shape.

Runtime coherence is a tuple:

```text
checked-out CLI version
+ configured release pin
+ executable CLI version
+ supported/current database schema
```

Task-state output must not present itself as authoritative when that tuple is
incoherent.

## Application Flow

1. Parse a typed story lifecycle update.
2. Reject interactive transitions to `implemented` before persistence.
3. Route completion through the existing fresh-proof transaction.
4. Open SQL-query execution with SQLite read-only/query-only enforcement.
5. Resolve and report runtime coherence before broad state retrieval.
6. Filter matrix records in the application/domain layer without changing
   protocol-v1 work-graph envelopes.
7. Select context and logging obligations from request class and risk lane.
8. Run contract/doc/eval checks in pull-request CI and again for releases.

## Interface Contract

- Existing valid commands and protocol-v1 JSON envelopes remain compatible.
- Rejected completion bypasses return actionable text and machine errors that
  direct callers to configure proof and use `story complete`.
- `query sql` retains read queries and rejects mutating SQL.
- New coherence and matrix filters are additive.
- Default human output becomes smaller only where documentation and tests define
  the change explicitly; machine orchestration collections retain stable shapes.

## Data Model

No schema migration is planned. Enforcement operates at command/application and
SQLite connection boundaries. Existing implemented history remains readable and
replayable.

## UI / Platform Impact

CLI behavior and installer/refresh instruction parity affect macOS, Linux, and
Windows. Platform tests must cover both Bash and PowerShell-generated shims.

## Observability

Negative tests are first-class evidence: rejected transition, rejected SQL
write, incoherent runtime, read-only audit task, and stale-shim fixtures. Harness
task traces remain provenance records and are not relabeled as runtime telemetry.

## Alternatives Considered

1. Keep bypasses as trusted administrative shortcuts. Rejected because they use
   ordinary agent-facing commands and invalidate downstream completion claims.
2. Detect mutating SQL through keyword matching. Rejected because SQLite syntax,
   pragmas, CTEs, triggers, and `RETURNING` make lexical checks incomplete.
3. Commit platform binaries and the operational database. Rejected because they
   are platform/local state; coherence should be checked and bootstrapped instead.
4. Load all Harness context and rely on larger model windows. Rejected because
   relevance and instruction consistency matter independently of context size.

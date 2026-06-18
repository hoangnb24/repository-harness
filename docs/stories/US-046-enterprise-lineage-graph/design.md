# Design

## Domain Model

`LineageGraph` is an additive JSON artifact with:

- source-system nodes for CSV directories or connector sources;
- schema nodes from DBML parsing or connector introspection;
- table and column nodes from the normalized `Schema`;
- relationship nodes from `relationship_graph.json`;
- profiler-stage nodes from `run_summary.json`;
- artifact nodes from runtime artifact paths.

Edges are typed dependencies, such as source provides table, table has column,
schema defines table, relationship uses table/column, stage writes artifact,
and artifact supports artifact.

## Application Flow

1. The existing pipeline parses schema, catalogs sources, profiles data, runs
   quality and relationship checks, builds deterministic machine artifacts, and
   registers runtime artifacts.
2. Before deterministic reports render, the lineage builder receives the
   already-built artifacts plus a current runtime summary and events snapshot.
3. `lineage_graph.json` is written and registered as a runtime artifact.
4. Markdown/HTML reports render with a lineage summary and link.
5. The web runner includes `lineage_graph.json` in canonical artifact and
   dashboard discovery lists.

## Interface Contract

Additive artifact:

```json
{
  "artifact": "lineage_graph",
  "version": 1,
  "summary": {
    "source_system_count": 1,
    "table_count": 0,
    "column_count": 0,
    "relationship_count": 0,
    "stage_count": 0,
    "artifact_count": 0,
    "edge_count": 0
  },
  "evidence_artifacts": [
    "schema_parse_report.json",
    "schema_evaluation.json",
    "relationship_graph.json",
    "run_events.jsonl",
    "run_summary.json"
  ],
  "nodes": [],
  "edges": [],
  "warnings": []
}
```

Existing artifact names and output directories remain unchanged.

## Data Model

No persistent database changes. `lineage_graph.json` stores bounded metadata
only and must not embed raw CSV rows, connector extracts, passwords, tokens, or
unredacted connection URLs.

## UI / Platform Impact

The local web runner remains bound to `127.0.0.1`. The dashboard fetches the
lineage artifact through protected artifact URLs and can link it from relevant
drilldowns. It remains a generated-artifact consumer.

## Observability

Lineage stage and artifact relationships are derived from `run_summary.json`
and `run_events.jsonl` snapshots. Runtime redaction and connector redaction are
applied before lineage output is written.

## Alternatives Considered

1. External lineage catalog publishing. Rejected for this slice because the
   product is local-first and no database/external writes are in scope.
2. Inferring transform lineage from SQL. Rejected because the current profiler
   artifacts prove source, schema, checks, stages, and artifact dependencies,
   not arbitrary transformation lineage.
3. A JavaScript-only dashboard lineage graph. Rejected because lineage facts
   should be produced by the existing Python pipeline and exposed as a machine
   artifact.

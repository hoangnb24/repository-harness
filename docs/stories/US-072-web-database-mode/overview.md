# Overview

## Current Behavior

The local web runner supports browser upload mode and local path mode for DBML
plus CSV inputs. Postgres and MySQL/MariaDB connectors exist in the CLI, but
the web runner does not expose a first-class database source mode.

## Target Behavior

The local web runner exposes Database mode alongside Upload and Local path. A
user can choose Postgres or MySQL/MariaDB, enter a local connection URL,
schema/database, optional comma-separated table list, optional target column,
and the existing L4 report mode. The backend runs the existing connector
pipeline, generates the same Smart EDA artifacts, and keeps raw credentials out
of persisted manifests, job payloads, logs, reports, and dashboard data.

## Affected Users

- Data scientists profiling relational tables directly from a local database.
- Demo reviewers who need to see the run flow and artifacts from a database
  source without switching to the CLI.

## Affected Product Docs

- `docs/product/vsf-data-profiler.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `.interface-design/system.md`

## Non-Goals

- Do not build a hosted database connector.
- Do not mutate database data.
- Do not persist full raw connector CSV extracts.
- Do not add new production monitoring, backup, or security-audit behavior.

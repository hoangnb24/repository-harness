# Design

## Domain Model

`ExportPackage` is an additive artifact set derived from an existing VSF output
directory:

- `export_manifest.json`: package metadata, source run summary, included files,
  SHA-256 checksums, byte sizes, exclusions, and redaction scan status.
- `index.html`: self-contained package entrypoint linking copied artifacts and
  summarizing verdict, charts, lineage, relationship, schema, connector, and
  runtime evidence.
- Optional zip archive: deterministic archive of the package directory.

The package command is a presenter/copy step. It must not profile data, infer
new validation results, or read source CSV directories.

## Application Flow

1. Validate `--input` as an existing run output directory.
2. Validate/create `--output` as the package directory.
3. Discover allowed generated artifacts:
   - canonical JSON and report artifacts;
   - `charts/*.json`;
   - `samples/*.csv`;
   - optional L4 and connector artifacts.
4. Exclude raw source CSVs, hidden connector extract directories, temp files,
   and package-generated files from previous runs.
5. Copy included files under stable relative paths.
6. Compute SHA-256 checksums and sizes for copied files.
7. Scan copied text artifacts for secret-like raw values and known sensitive
   markers.
8. Render `index.html`.
9. Write `export_manifest.json`.
10. Optionally write a deterministic zip archive from package contents.

## Interface Contract

New CLI command:

```bash
vsf-profiler package \
  --input outputs/demo_small \
  --output outputs/demo_small_package \
  --zip
```

Output:

```text
outputs/demo_small_package/
  index.html
  export_manifest.json
  report.html
  report.md
  charts/*.json
  samples/*.csv
  ...
outputs/demo_small_package.zip
```

The command exits non-zero for missing inputs, missing required run artifacts,
or failed redaction scans.

## Data Model

No persistent database changes. No source CSV copying. `export_manifest.json`
contains package metadata and checksums only.

## UI / Platform Impact

`index.html` is a static offline entrypoint using inline CSS and links to local
package files. It follows the existing warm technical dashboard style but avoids
JavaScript and external assets so it can be opened directly from disk.

## Observability

The manifest records included artifacts, excluded path patterns, warnings,
source `run_summary.json` metadata, created time, package version, redaction
status, and zip metadata when generated.

## Alternatives Considered

1. Add package generation to every `run_pipeline()` execution. Rejected because
   the requested operation packages an existing output directory and should not
   change deterministic run artifacts by default.
2. Zip the output directory wholesale. Rejected because raw CSV/temp connector
   extracts must never be included accidentally.
3. Serve the package through the web runner. Rejected because the package must
   work offline without a local server.

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import typer

from vsf_profiler.chart_specs import build_chart_specs
from vsf_profiler.connectors import (
    DEFAULT_MYSQL_CHUNK_ROWS,
    DEFAULT_MYSQL_SCHEMA,
    DEFAULT_MYSQL_URL_ENV,
    DEFAULT_POSTGRES_CHUNK_ROWS,
    DEFAULT_POSTGRES_SCHEMA,
    DEFAULT_POSTGRES_URL_ENV,
    MySQLConnector,
    PostgresConnector,
    TabularSourceConnector,
    cleanup_connector_extracts,
)
from vsf_profiler.csv_catalog import build_catalog
from vsf_profiler.dataset_verdict import build_dataset_verdict
from vsf_profiler.dbml_parser import parse_dbml_with_report
from vsf_profiler.demo_data import create_small_demo, download_olist
from vsf_profiler.doctor import (
    build_doctor_report,
    format_doctor_report,
    has_required_failures,
)
from vsf_profiler.duckdb_utils import connect
from vsf_profiler.export_package import create_analysis_package
from vsf_profiler.influence_analyzer import (
    MAX_ANALYSIS_ROWS,
    MAX_FEATURE_COLUMNS,
    analyze_influence,
)
from vsf_profiler.issue_catalog import IssueCatalog
from vsf_profiler.lineage_graph import build_lineage_graph, read_run_events
from vsf_profiler.llm_narrative import (
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_MODEL,
    FakeNarrativeProvider,
    NarrativeProvider,
    OpenAINarrativeProvider,
    generate_l4_narrative,
)
from vsf_profiler.profiler import profile_dataset
from vsf_profiler.quality_rules import run_quality_checks
from vsf_profiler.relationship_checker import run_relationship_checks
from vsf_profiler.relationship_graph import build_relationship_graph
from vsf_profiler.report_generator import generate_reports
from vsf_profiler.runtime import RuntimeRecorder
from vsf_profiler.schema_diagram import build_schema_diagram
from vsf_profiler.schema_evaluation import build_schema_evaluation
from vsf_profiler.table_assessments import build_table_assessments


app = typer.Typer(help="VSF Data Profiler CLI")
demo_app = typer.Typer(help="Demo dataset commands")
app.add_typer(demo_app, name="demo")


@app.command()
def run(
    dbml_arg: Optional[Path] = typer.Argument(None, help="Optional positional DBML path."),
    dbml: Optional[Path] = typer.Option(None, "--dbml", help="DBML schema path."),
    csv_dir: Optional[Path] = typer.Option(None, "--csv-dir", help="Directory containing CSV files."),
    rules: Optional[Path] = typer.Option(None, "--rules", help="Optional YAML rules file."),
    target: Optional[str] = typer.Option(None, "--target", help="Target column as table.column."),
    out: Path = typer.Option(..., "--out", help="Output directory."),
    postgres_url: Optional[str] = typer.Option(
        None,
        "--postgres-url",
        help="Optional Postgres connection URL. Prefer --postgres-url-env for secrets.",
    ),
    postgres_url_env: str = typer.Option(
        DEFAULT_POSTGRES_URL_ENV,
        "--postgres-url-env",
        help="Environment variable containing the Postgres connection URL.",
    ),
    postgres_schema: str = typer.Option(
        DEFAULT_POSTGRES_SCHEMA,
        "--postgres-schema",
        help="Postgres schema to scan when --postgres-tables omits schema names.",
    ),
    postgres_tables: Optional[str] = typer.Option(
        None,
        "--postgres-tables",
        help="Comma-separated selected Postgres tables as table or schema.table.",
    ),
    postgres_chunk_rows: int = typer.Option(
        DEFAULT_POSTGRES_CHUNK_ROWS,
        "--postgres-chunk-rows",
        min=1,
        help="Rows fetched per Postgres chunk while extracting to DuckDB-readable files.",
    ),
    mysql_url: Optional[str] = typer.Option(
        None,
        "--mysql-url",
        help="Optional MySQL/MariaDB connection URL. Prefer --mysql-url-env for secrets.",
    ),
    mysql_url_env: str = typer.Option(
        DEFAULT_MYSQL_URL_ENV,
        "--mysql-url-env",
        help="Environment variable containing the MySQL/MariaDB connection URL.",
    ),
    mysql_schema: str = typer.Option(
        DEFAULT_MYSQL_SCHEMA,
        "--mysql-schema",
        help="MySQL database/schema to scan when --mysql-tables omits schema names.",
    ),
    mysql_tables: Optional[str] = typer.Option(
        None,
        "--mysql-tables",
        help="Comma-separated selected MySQL tables as table or schema.table.",
    ),
    mysql_chunk_rows: int = typer.Option(
        DEFAULT_MYSQL_CHUNK_ROWS,
        "--mysql-chunk-rows",
        min=1,
        help="Rows fetched per MySQL chunk while extracting to DuckDB-readable files.",
    ),
    max_analysis_rows: int = typer.Option(
        MAX_ANALYSIS_ROWS,
        "--max-analysis-rows",
        min=1,
        help="Maximum rows materialized for bounded influence analysis.",
    ),
    max_feature_columns: int = typer.Option(
        MAX_FEATURE_COLUMNS,
        "--max-feature-columns",
        min=1,
        help="Maximum feature columns materialized for bounded influence analysis.",
    ),
    use_llm: bool = typer.Option(False, "--use-llm", help="Generate optional L4 narrative."),
    llm_provider: Optional[str] = typer.Option(
        None,
        "--llm-provider",
        help="Optional narrative provider: 'fake' for local validation or 'openai'.",
    ),
) -> None:
    """Run profiling, validation, influence analysis, and report generation."""
    dbml_path = dbml or dbml_arg
    if llm_provider and not use_llm:
        raise typer.BadParameter("--llm-provider requires --use-llm.")
    source_connector = _source_connector_from_cli(
        postgres_url=postgres_url,
        postgres_url_env=postgres_url_env,
        postgres_schema=postgres_schema,
        postgres_tables=postgres_tables,
        postgres_chunk_rows=postgres_chunk_rows,
        mysql_url=mysql_url,
        mysql_url_env=mysql_url_env,
        mysql_schema=mysql_schema,
        mysql_tables=mysql_tables,
        mysql_chunk_rows=mysql_chunk_rows,
        csv_mode_requested=dbml_path is not None and csv_dir is not None,
    )
    if source_connector is None:
        if dbml_path is None:
            raise typer.BadParameter("Provide a DBML path with --dbml or as the first argument.")
        if csv_dir is None:
            raise typer.BadParameter("--csv-dir is required for CSV mode.")

    result = run_pipeline(
        dbml_path=dbml_path,
        csv_dir=csv_dir,
        rules_path=rules,
        target=target,
        out_dir=out,
        source_connector=source_connector,
        use_llm=use_llm,
        llm_provider=_llm_provider_from_config(llm_provider) if use_llm else None,
        max_analysis_rows=max_analysis_rows,
        max_feature_columns=max_feature_columns,
    )
    typer.echo(f"Wrote report: {result['report_html']}")
    typer.echo(f"Issues found: {result['issue_count']}")
    if result.get("l4_report"):
        typer.echo(f"Wrote L4 report: {result['l4_report']}")


@demo_app.command("create-small")
def demo_create_small(
    out: Path = typer.Option(Path("data/demo_small"), "--out", help="Output directory."),
) -> None:
    """Create a small local demo dataset with known injected defects."""
    root = create_small_demo(out)
    typer.echo(f"Created small demo dataset: {root}")


@demo_app.command("download-olist")
def demo_download_olist(
    out: Path = typer.Option(Path("data/olist"), "--out", help="Output directory."),
) -> None:
    """Download and unzip Olist data through the Kaggle CLI."""
    try:
        root = download_olist(out)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Downloaded Olist dataset: {root}")


@demo_app.command("run-olist")
def demo_run_olist(
    csv_dir: Path = typer.Option(Path("data/olist"), "--csv-dir", help="Olist CSV directory."),
    out: Path = typer.Option(Path("outputs/olist_demo"), "--out", help="Output directory."),
) -> None:
    """Run the Olist preset."""
    result = run_pipeline(
        dbml_path=Path("examples/olist/schema.dbml"),
        csv_dir=csv_dir,
        rules_path=Path("examples/olist/rules.yaml"),
        target="olist_order_reviews_dataset.review_score",
        out_dir=out,
    )
    typer.echo(f"Wrote report: {result['report_html']}")
    typer.echo(f"Issues found: {result['issue_count']}")


@app.command("web")
def web(
    port: int = typer.Option(
        8765,
        "--port",
        min=1,
        max=65535,
        help="Local web runner port. The server always binds 127.0.0.1.",
    ),
    run_root: Path = typer.Option(
        Path("outputs/web_runs"),
        "--run-root",
        help="Directory for uploaded inputs and generated web-run artifacts.",
    ),
) -> None:
    """Start the local-only browser runner for uploaded DBML/CSV jobs."""
    from vsf_profiler.web_runner import run_web_server

    run_web_server(port=port, run_root=run_root)


@app.command("doctor")
def doctor_command() -> None:
    """Check local release-candidate prerequisites without printing secrets."""
    report = build_doctor_report()
    typer.echo(format_doctor_report(report))
    if has_required_failures(report):
        raise typer.Exit(code=1)


@app.command("package")
def package_command(
    input_dir: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Existing VSF output directory to package.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory that will receive the self-contained analysis package.",
    ),
    zip_archive: bool = typer.Option(
        False,
        "--zip/--no-zip",
        help="Also write a deterministic zip archive next to the package directory.",
    ),
    pdf: bool = typer.Option(
        False,
        "--pdf/--no-pdf",
        help="Also render analysis_report.pdf from the existing package report artifacts.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Replace an existing package directory or zip archive.",
    ),
) -> None:
    """Package an existing profiler output directory for offline review."""
    try:
        result = create_analysis_package(
            input_dir=input_dir,
            output_dir=output_dir,
            create_zip=zip_archive,
            create_pdf=pdf,
            force=force,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Wrote analysis package: {result.output_dir}")
    typer.echo(f"Wrote export manifest: {result.manifest_path}")
    typer.echo(f"Wrote package index: {result.index_path}")
    if result.pdf_path:
        typer.echo(f"Wrote PDF report: {result.pdf_path}")
    if result.zip_path:
        typer.echo(f"Wrote package archive: {result.zip_path}")


def run_pipeline(
    *,
    dbml_path: Path | None,
    csv_dir: Path | None,
    rules_path: Path | None,
    target: str | None,
    out_dir: Path,
    source_connector: TabularSourceConnector | None = None,
    use_llm: bool = False,
    llm_provider: NarrativeProvider | None = None,
    max_analysis_rows: int = MAX_ANALYSIS_ROWS,
    max_feature_columns: int = MAX_FEATURE_COLUMNS,
) -> dict[str, str | int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    samples_dir = out_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    if source_connector is None:
        if dbml_path is None:
            raise ValueError("dbml_path is required for CSV mode.")
        if csv_dir is None:
            raise ValueError("csv_dir is required for CSV mode.")
        runtime_inputs: dict[str, Any] = {
            "source_type": "csv",
            "dbml_path": str(dbml_path),
            "csv_dir": str(csv_dir),
            "rules_path": str(rules_path) if rules_path else None,
            "target": target,
        }
    else:
        runtime_inputs = {
            **source_connector.runtime_inputs(),
            "dbml_path": str(dbml_path) if dbml_path else None,
            "rules_path": str(rules_path) if rules_path else None,
            "target": target,
        }
    if use_llm:
        runtime_inputs["use_llm"] = True
        runtime_inputs["llm_provider"] = getattr(llm_provider, "name", "none")
    if max_analysis_rows != MAX_ANALYSIS_ROWS:
        runtime_inputs["max_analysis_rows"] = max_analysis_rows
    if max_feature_columns != MAX_FEATURE_COLUMNS:
        runtime_inputs["max_feature_columns"] = max_feature_columns
    runtime = RuntimeRecorder(
        out_dir=out_dir,
        inputs=runtime_inputs,
    )
    runtime.start()
    runtime.declare_artifact(samples_dir, key="samples_dir")

    issue_catalog: IssueCatalog | None = None
    con = None
    connector_cleanup_paths: list[Path] = []
    connector_metadata: dict[str, Any] | None = None
    try:
        with runtime.stage("parse_dbml_schema", "Parse DBML schema") as stage:
            if dbml_path is not None:
                parse_result = parse_dbml_with_report(dbml_path)
                schema = parse_result.schema
                schema_parse_report = parse_result.report
            elif source_connector is not None:
                schema, schema_parse_report = source_connector.prepare_schema()
            else:
                raise ValueError("DBML path is required unless a connector supplies schema.")
            stage.add_detail("table_count", len(schema.tables))
            stage.add_detail("relationship_count", len(schema.relationships))
            stage.add_detail("diagnostic_count", len(schema_parse_report["diagnostics"]))
            stage.add_detail(
                "unsupported_construct_count",
                len(schema_parse_report["unsupported_constructs"]),
            )

        with runtime.stage("catalog_csv_files", "Catalog CSV files and table mappings") as stage:
            if source_connector is None:
                if csv_dir is None:
                    raise ValueError("csv_dir is required for CSV mode.")
                catalog = build_catalog(csv_dir, schema)
            else:
                catalog, connector_metadata, connector_cleanup_paths = source_connector.build_catalog(
                    schema=schema,
                    out_dir=out_dir,
                )
                stage.add_detail("source_type", source_connector.source_type)
                stage.add_detail(
                    "connector_warning_count",
                    len(connector_metadata.get("warnings", [])),
                )
            stage.add_detail("mapped_table_count", len(catalog.tables))
            stage.add_detail("missing_table_count", len(catalog.missing_tables))
            stage.add_detail("extra_csv_count", len(catalog.extra_csvs))

        try:
            with runtime.stage("profile_csv_tables", "Profile CSV tables and columns") as stage:
                con = connect()
                profile = profile_dataset(schema, catalog, con=con)
                stage.add_detail("table_count", len(profile.tables))
                stage.add_detail("row_count", sum(table.row_count for table in profile.tables.values()))
                stage.add_detail(
                    "column_count",
                    sum(table.column_count for table in profile.tables.values()),
                )

            issue_catalog = IssueCatalog(samples_dir=samples_dir, con=con)
            with runtime.stage("data_quality_checks", "Run data quality checks") as stage:
                run_quality_checks(
                    con=con,
                    schema=schema,
                    catalog=catalog,
                    profile=profile,
                    issues=issue_catalog,
                    rules_path=rules_path,
                )
                stage.add_detail("issue_count", len(issue_catalog.issues))

            with runtime.stage("relationship_checks", "Check relationships") as stage:
                issue_count_before = len(issue_catalog.issues)
                relationship_summary = run_relationship_checks(
                    con=con,
                    schema=schema,
                    catalog=catalog,
                    profile=profile,
                    issues=issue_catalog,
                )
                profile.relationships = relationship_summary
                stage.add_detail("relationship_count", len(relationship_summary))
                stage.add_detail(
                    "issue_count_added",
                    len(issue_catalog.issues) - issue_count_before,
                )

            with runtime.stage("influence_analysis", "Run influence analysis") as stage:
                influence = analyze_influence(
                    con=con,
                    schema=schema,
                    catalog=catalog,
                    target=target,
                    max_analysis_rows=max_analysis_rows,
                    max_feature_columns=max_feature_columns,
                )
                stage.add_detail("row_count", influence.row_count)
                stage.add_detail("feature_count", len(influence.top_features))
                if not target:
                    stage.mark_skipped("No target column was provided.")
                elif influence.notes and not influence.top_features:
                    stage.add_detail("notes", influence.notes)
        finally:
            if con is not None:
                con.close()

        with runtime.stage("write_machine_artifacts", "Write machine-readable artifacts") as stage:
            schema_diagram = build_schema_diagram(schema, catalog, out_dir)
            profile_summary_payload = profile.model_dump(mode="json")
            issues_payload = [issue.model_dump(mode="json") for issue in issue_catalog.issues]
            influence_payload = influence.model_dump(mode="json")
            schema_evaluation = build_schema_evaluation(
                schema=schema,
                catalog=catalog,
                issues=issue_catalog.issues,
            )
            relationship_graph = build_relationship_graph(
                schema=schema,
                catalog=catalog,
                profile=profile,
                relationship_summaries=relationship_summary,
                issues=issue_catalog.issues,
            )
            dataset_verdict = build_dataset_verdict(
                issues=issue_catalog.issues,
                schema_evaluation=schema_evaluation,
                relationship_graph=relationship_graph,
            )
            table_assessments = build_table_assessments(
                profile=profile,
                issues=issue_catalog.issues,
                relationship_graph=relationship_graph,
            )
            chart_specs = build_chart_specs(
                profile_summary=profile_summary_payload,
                issues=issues_payload,
                relationship_graph=relationship_graph,
                dataset_verdict=dataset_verdict,
                influence=influence_payload,
            )
            runtime.artifact_written(
                out_dir / "schema_diagram.dbml",
                key="schema_diagram_dbml",
                kind="schema_diagram",
            )
            _write_json(
                out_dir / "profile_summary.json",
                profile_summary_payload,
                runtime=runtime,
                key="profile_summary",
            )
            _write_json(
                out_dir / "issues.json",
                issues_payload,
                runtime=runtime,
                key="issues",
            )
            _write_json(
                out_dir / "influence.json",
                influence_payload,
                runtime=runtime,
                key="influence",
            )
            _write_json(
                out_dir / "schema_parse_report.json",
                schema_parse_report,
                runtime=runtime,
                key="schema_parse_report",
            )
            if connector_metadata is not None:
                _write_json(
                    out_dir / "connector_metadata.json",
                    connector_metadata,
                    runtime=runtime,
                    key="connector_metadata",
                )
            _write_json(
                out_dir / "schema_diagram.json",
                schema_diagram,
                runtime=runtime,
                key="schema_diagram_json",
            )
            _write_json(
                out_dir / "schema_evaluation.json",
                schema_evaluation,
                runtime=runtime,
                key="schema_evaluation",
            )
            _write_json(
                out_dir / "relationship_graph.json",
                relationship_graph,
                runtime=runtime,
                key="relationship_graph",
            )
            _write_json(
                out_dir / "dataset_verdict.json",
                dataset_verdict,
                runtime=runtime,
                key="dataset_verdict",
            )
            _write_json(
                out_dir / "table_assessments.json",
                table_assessments,
                runtime=runtime,
                key="table_assessments",
            )
            _write_chart_specs(out_dir / "charts", chart_specs, runtime=runtime)
            runtime.set_issue_counts(issue_catalog.issues)
            stage.add_detail("artifact_count", len(runtime.report_context()["artifact_paths"]))
            stage.add_detail("chart_spec_count", len(chart_specs))
            stage.add_detail(
                "table_assessment_count",
                table_assessments["summary"]["table_count"],
            )

        l4_report_path: Path | None = None
        if use_llm:
            with runtime.stage("llm_narrative", "Generate optional L4 narrative") as stage:
                narrative_result = generate_l4_narrative(
                    out_dir=out_dir,
                    artifacts={
                        "profile_summary": profile_summary_payload,
                        "issues": issues_payload,
                        "influence": influence_payload,
                        "schema_evaluation": schema_evaluation,
                        "relationship_graph": relationship_graph,
                        "dataset_verdict": dataset_verdict,
                        "table_assessments": table_assessments,
                        "chart_specs": chart_specs,
                    },
                    provider=llm_provider,
                )
                l4_report_path = narrative_result["l4_report_path"]
                runtime.artifact_written(l4_report_path, key="l4_report", kind="llm_report")
                runtime.artifact_written(
                    narrative_result["guardrail_report_path"],
                    key="guardrail_report",
                    kind="guardrail_report",
                    details={
                        "status": narrative_result["guardrail_report"]["status"],
                        "provider": narrative_result["guardrail_report"]["provider"],
                        "model": narrative_result["guardrail_report"].get("model", ""),
                        "fallback_reason": narrative_result["guardrail_report"].get(
                            "fallback_reason",
                            "",
                        ),
                    },
                )
                guardrail_report = narrative_result["guardrail_report"]
                stage.add_detail("provider", guardrail_report["provider"])
                stage.add_detail("guardrail_status", guardrail_report["status"])
                if guardrail_report.get("model"):
                    stage.add_detail("model", guardrail_report["model"])
                if guardrail_report.get("fallback_reason"):
                    stage.add_detail("fallback_reason", guardrail_report["fallback_reason"])
                stage.add_detail("l4_report_path", "l4_report.md")

        with runtime.stage("render_reports", "Render Markdown and HTML reports") as stage:
            runtime.declare_artifact(out_dir / "report.md", key="report_md")
            runtime.declare_artifact(out_dir / "report.html", key="report_html")
            generate_reports(
                out_dir=out_dir,
                profile=profile,
                issues=issue_catalog.issues,
                influence=influence,
                schema_diagram=schema_diagram,
                schema_parse_report=schema_parse_report,
                connector_metadata=connector_metadata,
                schema_evaluation=schema_evaluation,
                relationship_graph=relationship_graph,
                dataset_verdict=dataset_verdict,
                table_assessments=table_assessments,
                chart_specs=chart_specs,
                run_summary=runtime.report_context(status="success"),
            )
            stage.add_detail("report_count", 2)
            stage.add_detail("formats", ["markdown", "html"])

        runtime.declare_artifact(out_dir / "lineage_graph.json", key="lineage_graph")
        lineage_graph = build_lineage_graph(
            schema=schema,
            catalog=catalog,
            profile_summary=profile_summary_payload,
            issues=issues_payload,
            schema_parse_report=schema_parse_report,
            schema_evaluation=schema_evaluation,
            relationship_graph=relationship_graph,
            dataset_verdict=dataset_verdict,
            table_assessments=table_assessments,
            chart_specs=chart_specs,
            run_summary=runtime.report_context(status="success"),
            run_events=read_run_events(runtime.events_path),
            connector_metadata=connector_metadata,
        )
        _write_json(
            out_dir / "lineage_graph.json",
            lineage_graph,
            runtime=runtime,
            key="lineage_graph",
        )
        generate_reports(
            out_dir=out_dir,
            profile=profile,
            issues=issue_catalog.issues,
            influence=influence,
            schema_diagram=schema_diagram,
            schema_parse_report=schema_parse_report,
            connector_metadata=connector_metadata,
            lineage_graph=lineage_graph,
            schema_evaluation=schema_evaluation,
            relationship_graph=relationship_graph,
            dataset_verdict=dataset_verdict,
            table_assessments=table_assessments,
            chart_specs=chart_specs,
            run_summary=runtime.report_context(status="success"),
        )
        runtime.artifact_written(out_dir / "report.md", key="report_md", kind="report")
        runtime.artifact_written(out_dir / "report.html", key="report_html", kind="report")
        runtime.finish_success(issues=issue_catalog.issues)
    except Exception as exc:
        runtime.finish_failed(
            exc,
            issues=issue_catalog.issues if issue_catalog is not None else [],
        )
        raise
    finally:
        cleanup_connector_extracts(connector_cleanup_paths)

    return {
        "report_html": str(out_dir / "report.html"),
        "issue_count": len(issue_catalog.issues),
        "l4_report": str(l4_report_path) if l4_report_path else "",
    }


def _write_json(
    path: Path,
    payload: Any,
    *,
    runtime: RuntimeRecorder | None = None,
    key: str | None = None,
) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    if runtime is not None:
        runtime.artifact_written(path, key=key, kind="json")


def _write_chart_specs(
    charts_dir: Path,
    chart_specs: dict[str, dict[str, Any]],
    *,
    runtime: RuntimeRecorder | None = None,
) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    if runtime is not None:
        runtime.declare_artifact(charts_dir, key="charts_dir")
    for filename, payload in chart_specs.items():
        key = f"chart_{Path(filename).stem}"
        _write_json(charts_dir / filename, payload, runtime=runtime, key=key)


def _source_connector_from_cli(
    *,
    postgres_url: str | None,
    postgres_url_env: str,
    postgres_schema: str,
    postgres_tables: str | None,
    postgres_chunk_rows: int,
    mysql_url: str | None,
    mysql_url_env: str,
    mysql_schema: str,
    mysql_tables: str | None,
    mysql_chunk_rows: int,
    csv_mode_requested: bool,
) -> TabularSourceConnector | None:
    explicit_postgres_requested = any(
        [
            postgres_url,
            postgres_tables,
            postgres_schema != DEFAULT_POSTGRES_SCHEMA,
            postgres_url_env != DEFAULT_POSTGRES_URL_ENV,
        ]
    )
    explicit_mysql_requested = any(
        [
            mysql_url,
            mysql_tables,
            mysql_schema != DEFAULT_MYSQL_SCHEMA,
            mysql_url_env != DEFAULT_MYSQL_URL_ENV,
        ]
    )
    postgres_env_has_url = bool(os.environ.get(postgres_url_env, "").strip())
    mysql_env_has_url = bool(os.environ.get(mysql_url_env, "").strip())
    postgres_requested = explicit_postgres_requested or (
        postgres_env_has_url and not csv_mode_requested
    )
    mysql_requested = explicit_mysql_requested or (mysql_env_has_url and not csv_mode_requested)
    if postgres_requested and mysql_requested:
        raise typer.BadParameter("Choose only one database connector: Postgres or MySQL.")
    if postgres_requested:
        return PostgresConnector.from_config(
            postgres_url=postgres_url,
            postgres_url_env=postgres_url_env,
            postgres_schema=postgres_schema,
            postgres_tables=postgres_tables,
            postgres_chunk_rows=postgres_chunk_rows,
        )
    if mysql_requested:
        return MySQLConnector.from_config(
            mysql_url=mysql_url,
            mysql_url_env=mysql_url_env,
            mysql_schema=mysql_schema,
            mysql_tables=mysql_tables,
            mysql_chunk_rows=mysql_chunk_rows,
        )
    if not postgres_requested and not mysql_requested:
        return None
    return None


def _llm_provider_from_config(name: str | None) -> NarrativeProvider | None:
    _load_env_file()
    provider_name = name or os.environ.get("VSF_PROFILER_LLM_PROVIDER")
    if provider_name is None:
        return None
    provider_name = provider_name.strip().lower()
    if provider_name == "fake":
        return FakeNarrativeProvider()
    if provider_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        try:
            return OpenAINarrativeProvider(
                api_key=api_key,
                model=os.environ.get("VSF_OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()
                or DEFAULT_OPENAI_MODEL,
                base_url=os.environ.get("VSF_OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).strip()
                or DEFAULT_OPENAI_BASE_URL,
                timeout_seconds=_env_float("VSF_OPENAI_TIMEOUT_SECONDS", 60.0),
                max_output_tokens=_env_int("VSF_OPENAI_MAX_OUTPUT_TOKENS", 1200),
            )
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid OpenAI L4 provider config: {exc}") from exc
    raise typer.BadParameter(
        f"Unsupported LLM provider '{provider_name}'. Supported providers: fake, openai."
    )


def _load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = raw_value.strip().strip('"').strip("'")
        os.environ[key] = value


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise typer.BadParameter(f"{name} must be an integer.") from exc
    if value <= 0:
        raise typer.BadParameter(f"{name} must be greater than zero.")
    return value


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise typer.BadParameter(f"{name} must be a number.") from exc
    if value <= 0:
        raise typer.BadParameter(f"{name} must be greater than zero.")
    return value

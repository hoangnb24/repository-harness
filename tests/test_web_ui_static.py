from pathlib import Path


def test_web_ui_contains_upload_mapping_and_visualization_regions():
    root = Path(__file__).resolve().parents[1] / "web"
    design_system = Path(__file__).resolve().parents[1] / ".interface-design" / "system.md"
    html = (root / "index.html").read_text()
    css = (root / "styles.css").read_text()
    js = (root / "app.js").read_text()
    design = design_system.read_text()

    required_html = [
        "Smart EDA Console",
        'id="dbmlInput"',
        'id="csvInput"',
        'id="visualizeButton"',
        'id="mappingBody"',
        'id="diagramFrame"',
        'id="localDiagram"',
        'id="diagramSvg"',
        'id="diagramMessage"',
        'id="diagramWarnings"',
        'id="diagramSourceBadge"',
        'id="diagramFitButton"',
        'id="diagramDensityToggle"',
        'id="diagramColumnsToggle"',
        'id="diagramResetSelection"',
        'id="diagramCanvas"',
        'id="diagramInspector"',
        'id="runnerForm"',
        'id="pathRunnerForm"',
        'id="runProfilerButton"',
        'id="runPathProfilerButton"',
        'id="dbmlPathInput"',
        'id="csvDirPathInput"',
        'id="rulesPathInput"',
        'id="stageList"',
        'id="artifactList"',
        'id="dashboard"',
        'id="dashboardPanelGrid"',
        'id="dashboardGraphModeLineage"',
        'id="dashboardGraphModeRelationship"',
        'id="dashboardGraphDisplayOverview"',
        'id="dashboardGraphDisplayFocus"',
        'id="dashboardGraphDisplayFull"',
        'id="dashboardGraphColumnsToggle"',
        'id="dashboardGraphRuntimeToggle"',
        'id="dashboardGraphInvalidOnlyToggle"',
        'id="dashboardGraphResetView"',
        'id="dashboardGraphScope"',
        'id="dashboardGraphStatus"',
        'id="dashboardGraphSvg"',
        'id="dashboardGraphLegend"',
        'id="dashboardGraphDrilldown"',
        "Reset graph view",
        "Invalid/warning only",
        'id="dashboardSeverityFilter"',
        'id="dashboardIssueTypeFilter"',
        'id="dashboardTableFilter"',
        'id="dashboardSummaryStrip"',
        'id="tableImpact"',
        'id="tableImpactGrid"',
        'id="tableImpactStatus"',
        'id="dashboardDrilldown"',
        "DBML diagram preview",
        "Local diagram preview renders from browser DBML state",
        "Fit view",
        "Expanded cards",
        "Show non-key columns",
        "Reset selection",
        "CSV to DBML Table Mapping",
        "Start a local Python/DuckDB run",
        "Generated results",
        "Dashboard",
        "Table Assessment",
        "Vercel serves static preflight only",
        "Upload mode",
        "Local path mode",
        "Preparing demo DBML diagram",
        "Reset demo",
    ]
    for marker in required_html:
        assert marker in html

    required_css_tokens = [
        "--surface-canvas",
        "--surface-panel",
        "--surface-rail",
        "--accent",
        "--focus-ring",
        ".diagram-role-bridge",
        ".diagram-inspector",
        ".diagram-edge-hit",
        ".pill-status.manual",
        ".pill-status.ambiguous",
        ".pill-status.failed",
        "@media (prefers-reduced-motion: reduce)",
    ]
    for marker in required_css_tokens:
        assert marker in css

    required_js = [
        "parseDbml",
        "parseCsvHeader",
        "autoLinkCsvs",
        "manualMappings",
        "mappingOverridesForRun",
        "checkRunnerHealth",
        "startProfilerRun",
        "startPathRun",
        "renderGeneratedResults",
        "renderGeneratedResultPreviews",
        "renderGeneratedL4Preview",
        "renderGeneratedReportLinks",
        "artifactUrlFromArtifacts",
        "loadDashboard",
        "renderDashboard",
        "renderDashboardSummary",
        "renderL4GuardrailPanel",
        "renderTableImpactSection",
        "renderDashboardDrilldown",
        "renderL4GuardrailDetails",
        "renderDashboardGraph",
        "guardrailStatusClass",
        "renderDiagram",
        "buildDiagramModel",
        "buildPreflightDiagramModel",
        "buildArtifactDiagramModel",
        "drawLocalDiagram",
        "layoutLocalDiagram",
        "diagramTableRole",
        "diagramVisibleColumns",
        "handleDiagramSelectionEvent",
        "renderDiagramInspector",
        "diagramSelectionContext",
        "localDiagramLimits",
        "Local DBML preview unavailable",
        "Diagram is too large for local preview",
        "Preparing demo DBML diagram",
        "schema_diagram.json",
        "schema_parse_report.json",
        "l4_report.md",
        "guardrail_report.json",
        "data-diagram-table",
        "data-diagram-relationship",
        "diagram-relationship",
        "buildLineageGraphView",
        "buildRelationshipGraphView",
        "dashboardGraphSelection",
        "dashboardGraphDisplay",
        "dashboardGraphShowColumns",
        "dashboardGraphShowRuntime",
        "dashboardGraphInvalidOnly",
        "applyDashboardGraphFocus",
        "graphSelectionContext",
        "renderGraphDirectConnections",
        "renderGraphTableColumns",
        "artifact-summary:generated",
        "EventSource",
        "loadDemoState();",
        "buildDbdiagramUrl",
        "https://dbdiagram.io/embed?c=",
    ]
    for marker in required_js:
        assert marker in js

    assert "restrained Smart EDA console" in design
    assert "Table Assessment" in design
    assert "Local ERD Diagram" in design
    assert "orthogonal elbow paths" in design
    assert "Georgia" not in css
    assert "radial-gradient" not in css
    assert "#fffaf0" not in css


def test_web_ui_uses_local_backend_runner_without_js_profiler_port():
    js = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text()
    assert 'fetch("/api/health"' in js
    assert 'fetch("/api/jobs"' in js
    assert 'fetch("/api/path-jobs"' in js
    assert 'fetch(`/api/jobs/${jobId}/dashboard`' in js
    assert "new EventSource" in js
    assert "run_events.jsonl" in js
    assert "run_summary.json" in js
    assert "charts/issue_counts_by_severity.json" in js
    assert "charts/issue_counts_by_type.json" in js
    assert "charts/missingness_by_table.json" in js
    assert "charts/outliers_top_columns.json" in js
    assert "charts/relationship_fk_health.json" in js
    assert "charts/influence_top_features.json" in js
    assert "renderOutliersPanel" in js
    assert "lineage_graph.json" in js
    assert "relationship_graph.json" in js
    assert "table_assessments.json" in js
    assert "guardrail_report.json" in js
    assert "renderTableImpactSection" in js
    assert "data-graph-node-id" in js
    assert "profile_dataset" not in js
    assert "run_quality_checks" not in js
    assert "XMLHttpRequest" not in js
    assert "diagramFrame.src =" not in js


def test_web_ui_path_mode_avoids_browser_directory_permission_api():
    root = Path(__file__).resolve().parents[1] / "web"
    html = (root / "index.html").read_text()
    js = (root / "app.js").read_text()

    assert "webkitdirectory" not in html
    assert "showDirectoryPicker" not in js


def test_web_dashboard_uses_artifacts_not_raw_csv_fetches():
    js = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text()

    assert "fetchCsv" not in js
    assert "fetchRawCsv" not in js
    assert 'fetch(".csv' not in js
    assert "fetch(`.csv" not in js
    assert "readFilePrefix" in js
    assert "fetchArtifactJson" in js
    assert "dashboardArtifactIndex" in js

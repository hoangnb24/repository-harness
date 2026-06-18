const { expect, test } = require("@playwright/test");
const fs = require("node:fs");

test("local path run renders the interactive dashboard from generated artifacts", async ({
  page,
}) => {
  const artifactRequests = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/jobs/") && url.includes("/artifacts/")) {
      artifactRequests.push(url);
    }
  });

  await page.goto("/");
  await expect(page.locator("#runnerMessage")).toContainText("Local backend is ready");
  await expect(page.locator("#localDiagram")).toBeVisible();
  await expect(page.locator("#diagramFrame")).toBeHidden();
  await expect(page.locator("#diagramSourceBadge")).toContainText("Browser DBML");
  await expect(page.locator("#diagramMessage")).toContainText("Local preflight");
  await expect(page.locator("#diagramSvg")).toContainText("orders");
  await expect(page.locator("#diagramSvg")).toContainText("PK order_id");
  await expect(page.locator("#diagramSvg")).toContainText("FK customer_id");
  await expect(page.locator('#diagramSvg [data-diagram-table="orders"]')).toHaveCount(1);
  await expect(page.locator("#diagramFitButton")).toBeVisible();
  await expect(page.locator("#diagramFitButton")).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#diagramDensityToggle")).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("#diagramColumnsToggle")).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator('#diagramSvg .diagram-role-bridge[data-diagram-table="order_items"]')).toHaveCount(1);
  await page.locator('#diagramSvg [data-diagram-table="orders"]').click();
  await expect(page.locator('#diagramSvg [data-diagram-table="orders"]')).toHaveClass(/selected/);
  await expect(page.locator("#diagramInspector")).toContainText("orders");
  await expect(page.locator("#diagramInspector")).toContainText("Fact/event");
  await page.locator("#diagramColumnsToggle").click();
  await expect(page.locator("#diagramColumnsToggle")).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#diagramSvg")).toContainText("order_status");
  await page.locator("#diagramResetSelection").click();
  await expect(page.locator('#diagramSvg [data-diagram-table="orders"]')).not.toHaveClass(/selected/);
  await expect(page.locator("#dbdiagramLink")).toHaveAttribute(
    "href",
    /https:\/\/dbdiagram\.io\/embed\?c=/,
  );

  await page.locator("#runnerModePath").click();
  await expect(page.locator("#pathRunnerForm")).toBeVisible();

  await page.locator("#dbmlPathInput").fill("data/demo_small/schema.dbml");
  await page.locator("#csvDirPathInput").fill("data/demo_small/csv");
  await page.locator("#rulesPathInput").fill("data/demo_small/rules.yaml");
  await page.locator("#pathTargetInput").fill("order_reviews.review_score");

  await expect(page.locator("#runPathProfilerButton")).toBeEnabled();
  await page.locator("#runPathProfilerButton").click();

  await expect(page.locator("#runnerMessage")).toContainText("Run complete", {
    timeout: 60_000,
  });
  await expect(page.locator("#dashboardMessage")).toContainText(
    /Dashboard loaded|Influence chart is absent/,
    { timeout: 20_000 },
  );

  await expect(page.locator("#dashboardStatusBadge")).toContainText(
    "succeeded dashboard",
  );
  await expect(page.locator("#dashboardIssueCount")).toContainText("15/15 issues");
  await expect(page.locator("#dashboardSummaryStrip")).toContainText("readiness");
  await expect(page.locator("#dashboardSummaryStrip")).toContainText("artifacts");
  await expect(page.locator("#diagramSourceBadge")).toContainText("schema_diagram.json");
  await expect(page.locator("#diagramMessage")).toContainText("Generated artifacts");
  await expect(page.locator("#diagramWarnings")).toContainText("schema_parse_report.json");
  await expect(page.locator("#diagramSvg")).toContainText("order_payments");
  await expect(page.locator("#diagramSvg")).toContainText("invalid");
  await expect(page.locator('#diagramSvg [data-diagram-table="order_payments"]')).toHaveCount(1);
  const customerRelationship = page.locator(
    '#diagramSvg [data-diagram-relationship="orders.customer_id->customers.customer_id"]',
  );
  await expect(customerRelationship).toHaveCount(1);
  await customerRelationship.focus();
  await customerRelationship.press("Enter");
  await expect(customerRelationship).toHaveClass(/selected/);
  await expect(page.locator("#diagramInspector")).toContainText("Relationship");
  await expect(page.locator("#diagramInspector")).toContainText("FOREIGN_KEY_NULL");
  await expect(page.locator("#diagramInspector")).toContainText("relationship_graph.json");
  await page.locator("#diagramDensityToggle").click();
  await expect(page.locator("#diagramDensityToggle")).toHaveAttribute("aria-pressed", "true");

  await expect(page.getByText("Generated results")).toBeVisible();
  const generatedResults = page.locator("#artifactList");
  await expect(generatedResults).toContainText("EDA readiness");
  await expect(generatedResults).toContainText("NOT_READY");
  await expect(generatedResults).toContainText("Issue counts");
  await expect(generatedResults).toContainText("15 issues");
  await expect(generatedResults).toContainText("Table impact");
  await expect(generatedResults).toContainText("7 tables");
  await expect(generatedResults).toContainText("Runtime summary");
  await expect(generatedResults).toContainText("8 stages");
  await expect(generatedResults).toContainText("Report HTML");
  await expect(generatedResults).toContainText("report.html");
  await expect(generatedResults).toContainText("Report Markdown");
  await expect(generatedResults).toContainText("report.md");
  await expect(generatedResults).toContainText("Raw artifact links");
  await expect(generatedResults).toContainText("dataset_verdict.json");

  const dashboard = page.locator("#dashboardPanelGrid");
  await expect(dashboard).toContainText("EDA readiness");
  await expect(dashboard).toContainText("Issue counts by severity");
  await expect(dashboard).toContainText("Issue counts by type");
  await expect(dashboard).toContainText("Missingness by table");
  await expect(dashboard).toContainText("Relationship FK health");
  await expect(dashboard).toContainText("Influence top features");

  await expect(page.locator("#tableImpact")).toContainText("Table Assessment");
  await expect(page.locator("#tableImpactStatus")).toContainText(
    "tables from table_assessments.json",
  );
  await expect(page.locator("#tableImpactGrid")).toContainText("order_reviews");

  await page
    .locator('#tableImpactGrid [data-dashboard-kind="table_assessment"][data-dashboard-value="order_reviews"]')
    .click();
  await expect(page.locator("#dashboardDrilldownMeta")).toContainText("order_reviews");
  await expect(page.locator("#dashboardDrilldown")).toContainText("feedback_signal_quality");
  await expect(page.locator("#dashboardDrilldown")).toContainText("table_assessments.json");

  await expect(page.locator("#dashboardGraphStatus")).toContainText("Lineage graph");
  await expect(page.locator("#dashboardGraphStatus")).toContainText("Overview");
  await expect
    .poll(async () => page.locator("#dashboardGraphSvg [data-graph-node-id]").count())
    .toBeGreaterThan(0);
  await expect(page.locator("#dashboardGraphLegend")).toContainText("Table");
  await expect(page.locator('#dashboardGraphSvg [data-graph-node-id^="column:"]')).toHaveCount(0);
  await expect(page.locator('#dashboardGraphSvg [data-graph-node-id^="stage:"]')).toHaveCount(0);
  await expect(page.locator('#dashboardGraphSvg [data-graph-node-id^="artifact:"]')).toHaveCount(0);

  await page
    .locator("#dashboardGraphSvg [data-graph-node-id]")
    .filter({ hasText: "orders" })
    .first()
    .click();
  await expect(page.locator("#dashboardGraphDrilldownMeta")).toContainText("orders");
  await expect(page.locator("#dashboardGraphDrilldown")).toContainText(
    "lineage_graph.json",
  );
  await expect(page.locator("#dashboardGraphDrilldown")).toContainText("Direct neighbors");
  await expect(page.locator("#dashboardGraphDrilldown")).toContainText("Columns in inspector");
  await expect(page.locator("#dashboardGraphSvg .graph-node.dimmed").first()).toBeVisible();

  await page.locator("#dashboardGraphDisplayFocus").click();
  await expect(page.locator("#dashboardGraphStatus")).toContainText("Focus");
  await expect(page.locator("#dashboardGraphSvg .graph-node.selected")).toHaveCount(1);
  await page.locator("#dashboardGraphResetView").click();
  await expect(page.locator("#dashboardGraphStatus")).toContainText("Overview");
  await expect(page.locator("#dashboardGraphDisplayOverview")).toHaveAttribute("aria-pressed", "true");
  fs.mkdirSync("outputs/graph_progressive_screenshots", { recursive: true });
  await page.locator(".dashboard-graph").screenshot({
    path: "outputs/graph_progressive_screenshots/lineage-overview.png",
  });

  await page.locator("#dashboardGraphModeRelationship").click();
  await expect(page.locator("#dashboardGraphStatus")).toContainText(
    "Relationship graph",
  );
  await expect(page.locator("#dashboardGraphStatus")).toContainText("Overview");
  await expect(
    page.locator('#dashboardGraphSvg [data-graph-node-id^="relationship-edge:"]'),
  ).toHaveCount(0);
  await page.locator("#dashboardGraphInvalidOnlyToggle").check();
  await expect(page.locator("#dashboardGraphStatus")).toContainText(
    "invalid/warning only",
  );
  await page.locator("#dashboardGraphDisplayFull").click();
  await expect(page.locator("#dashboardGraphStatus")).toContainText(
    "Relationships",
  );
  await expect
    .poll(async () =>
      page.locator('#dashboardGraphSvg [data-graph-node-id^="relationship-edge:"]').count(),
    )
    .toBeGreaterThan(0);
  await page
    .locator('#dashboardGraphSvg [data-graph-node-id^="relationship-edge:"]')
    .first()
    .click();
  await expect(page.locator("#dashboardGraphDrilldown")).toContainText(
    "relationship_graph.json",
  );
  await expect(page.locator("#dashboardGraphDrilldown")).toContainText(
    /ORPHAN_FOREIGN_KEY|FOREIGN_KEY_NULL|PARENT_KEY_DUPLICATE|CHILD_RELATIONSHIP_DUPLICATE/,
  );
  await page.locator(".dashboard-graph").screenshot({
    path: "outputs/graph_progressive_screenshots/relationship-full.png",
  });

  await expect(page.locator("#dashboardArtifactCount")).toContainText(/1[6-7] files/);
  await expect(page.locator("#dashboardArtifactLinks")).toContainText(
    "charts/issue_counts_by_severity.json",
  );
  await expect(page.locator("#dashboardArtifactLinks")).toContainText(
    "schema_parse_report.json",
  );
  await expect(page.locator("#dashboardArtifactLinks")).toContainText(
    "relationship_graph.json",
  );
  await expect(page.locator("#dashboardArtifactLinks")).toContainText(
    "table_assessments.json",
  );
  await expect(page.locator("#dashboardArtifactLinks")).toContainText(
    "lineage_graph.json",
  );

  await page.locator("#dashboardSeverityFilter").selectOption("P1");
  await expect(page.locator("#dashboardIssueCount")).toContainText("/15 issues");

  await page
    .locator('[data-dashboard-kind="severity"][data-dashboard-value="P1"]')
    .click();
  await expect(page.locator("#dashboardDrilldownMeta")).toContainText("P1");
  await expect(page.locator("#dashboardDrilldown")).toContainText("matching issues");
  await expect(page.locator("#dashboardDrilldown")).toContainText("sample CSV");

  const rawCsvArtifactRequests = artifactRequests.filter(
    (url) => url.endsWith(".csv") && !url.includes("/samples/"),
  );
  expect(rawCsvArtifactRequests).toEqual([]);

  fs.mkdirSync("outputs/web_demo_ux_screenshots", { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = "auto";
    const dashboard = document.querySelector("#dashboard");
    window.scrollTo(0, dashboard.offsetTop);
  });
  await page.waitForTimeout(100);
  await page.screenshot({
    path: "outputs/web_demo_ux_screenshots/desktop-dashboard.png",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = "auto";
    const tableImpact = document.querySelector("#tableImpact");
    window.scrollTo(0, tableImpact.offsetTop);
  });
  await page.waitForTimeout(100);
  await expect(page.locator("#tableImpact")).toBeVisible();
  await page.screenshot({
    path: "outputs/web_demo_ux_screenshots/mobile-dashboard.png",
  });
});

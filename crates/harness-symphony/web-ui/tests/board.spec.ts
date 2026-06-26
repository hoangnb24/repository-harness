import { expect, test } from "@playwright/test";

test("board renders task columns and detail controls", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Symphony work board" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Workspace navigation" })).toBeVisible();
  await expect(page.getByText("Safe to start")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ready", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Blocked", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "In Progress", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Review", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Needs Attention", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Done", exact: true })).toBeVisible();

  await page.getByPlaceholder("Find task").fill("US-052");
  await expect(page.getByRole("button", { name: /US-052/ })).toBeVisible();
  await page.getByRole("button", { name: /US-052/ }).click();

  const detail = page.getByRole("complementary", { name: "Selected work detail" });
  await expect(
    detail.getByRole("heading", { name: "Sync Approval And Done Transition" })
  ).toBeVisible();
  await expect(page.getByText("Blocked by")).toBeVisible();
  await expect(page.getByText("Unblocks")).toBeVisible();
  await expect(detail.getByText("Hierarchy")).toBeVisible();
  await expect(detail.getByRole("button", { name: "Start" })).toBeVisible();
});

test("sidebar renders dependency graph edges and selects tasks", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "US-056",
            title: "Simplify Kanban-First Controller",
            board_state: "Done",
            story_status: "implemented",
            lane: "normal",
            verify: "configured",
            blockers: [],
            unblocks: ["US-057"],
            parent_id: null,
            children: [],
            hierarchy_depth: 0,
            run_id: null,
            active_run: null,
            reason: "story implemented"
          },
          {
            id: "US-057",
            title: "Dependency Graph Sidebar View",
            board_state: "Ready",
            story_status: "planned",
            lane: "normal",
            verify: "configured",
            blockers: ["US-056"],
            unblocks: ["US-059"],
            parent_id: null,
            children: [],
            hierarchy_depth: 0,
            run_id: null,
            active_run: null,
            reason: "ready"
          },
          {
            id: "US-059",
            title: "Review Surface Density Pass",
            board_state: "Blocked",
            story_status: "planned",
            lane: "normal",
            verify: "configured",
            blockers: ["US-057"],
            unblocks: [],
            parent_id: null,
            children: [],
            hierarchy_depth: 0,
            run_id: null,
            active_run: null,
            reason: "waiting for US-057"
          }
        ]
      })
    });
  });

  await page.goto("/");

  const graph = page.getByRole("region", { name: "Dependency graph sidebar" });
  await expect(graph.getByRole("heading", { name: "Dependency graph" })).toBeVisible();
  await expect(graph.getByLabel("Dependency edges")).toContainText("US-056");
  await expect(graph.getByLabel("Dependency edges")).toContainText("US-057");
  await expect(graph.getByLabel("Dependency edges")).toContainText("US-059");

  await graph.getByRole("button", { name: /US-057 Ready Dependency Graph Sidebar View/ }).click();
  const detail = page.getByRole("complementary", { name: "Selected work detail" });
  await expect(detail.getByRole("heading", { name: "Dependency Graph Sidebar View" })).toBeVisible();
  await expect(detail.getByText("US-056")).toBeVisible();
  await expect(detail.getByText("US-059")).toBeVisible();
});

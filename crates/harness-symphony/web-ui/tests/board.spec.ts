import { expect, test } from "@playwright/test";

function boardItem(id: string, title: string, board_state: string) {
  return {
    id,
    title,
    board_state,
    story_status: board_state === "Done" ? "implemented" : "planned",
    lane: "normal",
    verify: "configured",
    blockers: [],
    unblocks: [],
    parent_id: null,
    children: [],
    hierarchy_depth: 0,
    run_id: null,
    active_run: null,
    reason: board_state === "Ready" ? "ready" : "story visible on the board",
    failure_summary: null
  };
}

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

  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(page.getByTestId("task-detail-overlay")).toHaveCSS("position", "fixed");
  await expect(
    detail.getByRole("heading", { name: "Sync Approval And Done Transition" })
  ).toBeVisible();
  await expect(page.getByText("Blocked by")).toBeVisible();
  await expect(page.getByText("Unblocks")).toBeVisible();
  await expect(detail.getByText("Hierarchy")).toBeVisible();
  await expect(detail.getByRole("button", { name: /Start/ })).toBeVisible();
});

test("task detail close button closes popup and plays bounded confetti", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [boardItem("US-062", "Task Detail Close Confetti", "Ready")]
      })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-062/ }).click();

  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail.getByRole("heading", { name: "Task Detail Close Confetti" })).toBeVisible();
  await detail.getByRole("button", { name: "Close selected work detail" }).click();

  await expect(detail).toBeHidden();
  await expect(page.getByTestId("task-close-confetti")).toBeVisible();
  await expect(page.getByRole("button", { name: /US-062/ })).toBeVisible();
  await expect(page.getByTestId("task-close-confetti-host")).toHaveCount(0, { timeout: 2000 });

  await page.getByRole("button", { name: /US-062/ }).click();
  await expect(page.getByRole("dialog", { name: "Selected work detail" })).toBeVisible();
});

test("task detail close keeps working with reduced motion confetti suppressed", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [boardItem("US-062", "Task Detail Close Confetti", "Ready")]
      })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-062/ }).click();

  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail).toBeVisible();
  await detail.getByRole("button", { name: "Close selected work detail" }).click();

  await expect(detail).toBeHidden();
  await expect(page.getByTestId("task-close-confetti-host")).toHaveCount(0);
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
  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail.getByRole("heading", { name: "Dependency Graph Sidebar View" })).toBeVisible();
  await expect(detail.getByText("US-056")).toBeVisible();
  await expect(detail.getByText("US-059")).toBeVisible();
});

test("board columns stay bounded and scroll dense task lists internally", async ({ page }) => {
  const denseReadyItems = Array.from({ length: 22 }, (_, index) =>
    boardItem(`US-9${String(index).padStart(2, "0")}`, `Dense ready task ${index + 1}`, "Ready")
  );
  const sparseItems = ["Blocked", "In Progress", "Review", "Needs Attention", "Done"].map((state, index) =>
    boardItem(`US-8${index}`, `${state} task`, state)
  );

  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ items: [...denseReadyItems, ...sparseItems] })
    });
  });

  await page.setViewportSize({ width: 1280, height: 820 });
  await page.goto("/");

  for (const state of ["Ready", "Blocked", "In Progress", "Review", "Needs Attention", "Done"]) {
    await expect(page.getByRole("region", { name: `${state} column` })).toBeVisible();
  }

  const readyColumn = page.getByRole("region", { name: "Ready column" });
  const readyTasks = page.locator('[aria-label="Ready tasks"]');
  const pageScrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const viewportHeight = await page.evaluate(() => window.innerHeight);
  const readyMetrics = await readyTasks.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
    scrollTop: element.scrollTop
  }));

  expect(readyMetrics.scrollHeight).toBeGreaterThan(readyMetrics.clientHeight);
  expect(pageScrollHeight).toBeLessThan(viewportHeight + 280);

  await readyTasks.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });

  await expect(readyColumn.getByRole("heading", { name: "Ready", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /US-921/ })).toBeVisible();
  await expect
    .poll(async () => readyTasks.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(readyMetrics.scrollTop);

  await page.setViewportSize({ width: 390, height: 760 });
  await expect(readyColumn).toBeVisible();
  const mobileReadyMetrics = await readyTasks.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight
  }));
  expect(mobileReadyMetrics.scrollHeight).toBeGreaterThan(mobileReadyMetrics.clientHeight);
  await readyColumn.getByRole("button", { name: /US-900/ }).click();
  await expect(page.getByRole("dialog", { name: "Selected work detail" })).toBeVisible();
});

test("needs attention tasks show failure reason and evidence", async ({ page }) => {
  const failureSummary = {
    category: "Codex app-server timeout",
    reason: "turn-state query timed out while waiting for Codex.",
    latest_event: "turn/completed status failed",
    latest_error: "turn-state query timed out while waiting for Codex.",
    run_id: "run_timeout",
    evidence_artifacts: [
      ".harness/runs/run_timeout/APP_SERVER_EVENTS.jsonl",
      ".harness/runs/run_timeout/RESULT.json"
    ],
    next_action: "Inspect APP_SERVER_EVENTS.jsonl and retry when safe."
  };

  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            ...boardItem("US-066", "Needs Attention Failure Explanation", "Needs Attention"),
            run_id: "run_timeout",
            reason: failureSummary.reason,
            failure_summary: failureSummary
          }
        ]
      })
    });
  });
  await page.route("**/api/runs/run_timeout/review", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "run_timeout",
        story_id: "US-066",
        status: "failed",
        outcome: "failed",
        summary: null,
        result: null,
        validation: null,
        changed_files: [],
        changeset_preview: null,
        pr_url: null,
        pr_status: "missing",
        artifact_paths: failureSummary.evidence_artifacts,
        suggested_next_action: failureSummary.next_action,
        failure_summary: failureSummary,
        events: [{ method: "turn/completed", params: { turn: { status: "failed", error: { message: failureSummary.latest_error } } } }]
      })
    });
  });

  await page.goto("/");

  await expect(page.getByRole("button", { name: /US-066/ })).toContainText(failureSummary.reason);
  await expect(page.getByRole("button", { name: /US-066/ })).toContainText("Codex app-server timeout");

  await page.getByRole("button", { name: /US-066/ }).click();
  const detail = page.getByRole("dialog", { name: "Selected work detail" });

  await expect(detail.getByText("Codex app-server timeout").first()).toBeVisible();
  await expect(detail.getByText("turn-state query timed out while waiting for Codex.").first()).toBeVisible();
  await expect(detail.getByText("turn/completed status failed").first()).toBeVisible();
  await expect(detail.getByText(".harness/runs/run_timeout/APP_SERVER_EVENTS.jsonl").first()).toBeVisible();
  await expect(detail.getByText("Inspect APP_SERVER_EVENTS.jsonl and retry when safe.").first()).toBeVisible();
});

test("review logs render readable chat and progress entries while preserving raw artifacts", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "US-060",
            title: "Human-Readable Chat Logs",
            board_state: "Review",
            story_status: "implemented",
            lane: "normal",
            verify: "configured",
            blockers: [],
            unblocks: [],
            parent_id: null,
            children: [],
            hierarchy_depth: 0,
            run_id: "run_chat",
            active_run: null,
            reason: "review run communication"
          }
        ]
      })
    });
  });
  await page.route("**/api/runs/run_chat/review", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "run_chat",
        story_id: "US-060",
        status: "completed",
        outcome: "completed",
        summary: "Readable logs implemented.",
        result: null,
        validation: { commands: [{ command: "npm --prefix crates/harness-symphony/web-ui run build", result: "pass" }] },
        changed_files: ["crates/harness-symphony/web-ui/src/main.tsx"],
        changeset_preview: null,
        pr_url: "https://example.test/pr/60",
        pr_status: "created",
        artifact_paths: [".harness/runs/run_chat/APP_SERVER_EVENTS.jsonl"],
        suggested_next_action: "Review the readable log.",
        events: [
          { method: "thread/started", params: { thread: { id: "thr_chat" }, timestamp: "2026-06-27T10:00:00Z" } },
          { method: "turn/started", params: { turn: { status: "inProgress" } } },
          { method: "item/agentMessage/delta", params: { itemId: "msg_1", delta: "Implemented " } },
          { method: "item/agentMessage/delta", params: { itemId: "msg_1", delta: "readable logs." } },
          { method: "turn/diff/updated", params: {} },
          { method: "turn/completed", params: { turn: { status: "completed" } } },
          { unsupported: true, note: "kept as fallback" }
        ]
      })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-060/ }).click();
  const detail = page.getByRole("dialog", { name: "Selected work detail" });

  await expect(detail.getByRole("heading", { name: "Run communication" })).toBeVisible();
  await expect(detail.getByText("Assistant", { exact: true })).toBeVisible();
  await expect(detail.getByText("Implemented readable logs.")).toBeVisible();
  await expect(detail.getByText("Run started")).toBeVisible();
  await expect(detail.getByText("Workspace diff updated")).toBeVisible();
  await expect(detail.getByText("Run finished")).toBeVisible();
  await expect(detail.getByText("Unsupported event payload with keys: unsupported, note.")).toBeVisible();
  await expect(detail.getByText("Raw artifact: APP_SERVER_EVENTS.jsonl")).toBeVisible();
  await expect(detail.getByText(".harness/runs/run_chat/APP_SERVER_EVENTS.jsonl")).toBeVisible();
});

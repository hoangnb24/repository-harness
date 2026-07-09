import { expect, test, type Locator, type Page } from "@playwright/test";

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
    failure_summary: null,
    recovery_action: null
  };
}

async function expectNoHorizontalOverflow(locator: Locator, label: string) {
  const overflow = await locator.evaluate(
    (element) => Math.ceil(element.scrollWidth) - Math.ceil(element.clientWidth)
  );
  expect(overflow, `${label} horizontal overflow`).toBeLessThanOrEqual(1);
}

async function expectPageNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => Math.ceil(document.documentElement.scrollWidth) - Math.ceil(window.innerWidth)
  );
  expect(overflow, "page horizontal overflow").toBeLessThanOrEqual(1);
}

async function expectReadableTaskCard(locator: Locator, label: string) {
  const box = await locator.boundingBox();
  expect(box?.height ?? 0, `${label} readable card height`).toBeGreaterThanOrEqual(124);
}

test("board renders task columns and detail controls", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Symphony Command Center" })).toBeVisible();
  await expect(page.getByText("Local operations surface")).toBeVisible();
  await expect(page.getByRole("region", { name: "Command status rail" })).toBeVisible();
  await expect(page.locator("#board")).toHaveClass(/command-board-surface/);
  await expect(page.getByRole("complementary", { name: "Workspace navigation" })).toBeVisible();
  await expect(page.getByText("Safe to start")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ready", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Blocked", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "In Progress", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Review", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Needs Attention", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Done", exact: true })).toBeVisible();

  await page.getByRole("textbox", { name: "Find task" }).fill("US-052");
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

test("task detail traps focus, closes with escape, and restores opener focus", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [boardItem("US-069", "Modal Focus Contract", "Ready")]
      })
    });
  });

  await page.goto("/");
  const opener = page.getByRole("button", { name: /US-069/ });
  await opener.click();

  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail).toBeVisible();
  for (let index = 0; index < 8; index += 1) {
    await page.keyboard.press("Tab");
    await expect
      .poll(async () =>
        detail.evaluate((element) => element.contains(document.activeElement))
      )
      .toBe(true);
  }

  await page.keyboard.press("Escape");
  await expect(detail).toBeHidden();
  await expect(opener).toBeFocused();
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

test("reduced motion suppresses operational spinner animation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [boardItem("US-069", "Reduced Motion Active Run", "In Progress")]
      })
    });
  });

  await page.goto("/");
  const spinner = page.locator("#column-in-progress svg").first();
  await expect(spinner).toBeVisible();
  await expect
    .poll(async () => spinner.evaluate((element) => getComputedStyle(element).animationName))
    .toBe("none");
});

test("board loading and failure states expose accessibility semantics", async ({ page }) => {
  let releaseBoard!: () => void;
  const boardReady = new Promise<void>((resolve) => {
    releaseBoard = resolve;
  });
  await page.route("**/api/board", async (route) => {
    await boardReady;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ items: [boardItem("US-069", "Accessible Board State", "Ready")] })
    });
  });

  const gotoPromise = page.goto("/");
  await expect(page.locator("#board")).toHaveAttribute("aria-busy", "true");
  await expect(page.getByRole("status")).toContainText("Loading Symphony board.");
  releaseBoard();
  await gotoPromise;
  await expect(page.locator("#board")).toHaveAttribute("aria-busy", "false");
  await expect(page.getByRole("status")).toContainText("Symphony board loaded.");

  await page.route("**/api/board", async (route) => {
    await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: "board unavailable" }) });
  });
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("board unavailable");
});

test("ready task delete action confirms, retires, and refreshes the board", async ({ page }) => {
  let retired = false;
  page.on("dialog", async (dialog) => {
    expect(dialog.message()).toContain("Retire US-064 Ready Work Story Delete Action");
    await dialog.accept();
  });
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: retired ? [] : [boardItem("US-064", "Ready Work Story Delete Action", "Ready")]
      })
    });
  });
  await page.route("**/api/tasks/US-064/retire", async (route) => {
    expect(route.request().method()).toBe("POST");
    retired = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ story_id: "US-064", status: "retired" })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-064/ }).click();
  const detail = page.getByRole("dialog", { name: "Selected work detail" });

  await expect(detail.getByRole("button", { name: "Delete work story" })).toBeVisible();
  await detail.getByRole("button", { name: "Delete work story" }).click();

  await expect.poll(async () => retired).toBe(true);
  await expect(detail).toBeHidden();
  await expect(page.getByRole("button", { name: /US-064/ })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Ready column" }).getByText("No tasks")).toBeVisible();
});

test("delete action is hidden for non-ready tasks", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          boardItem("US-064", "Blocked Delete Guard", "Blocked"),
          boardItem("US-065", "Done Delete Guard", "Done")
        ]
      })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-064/ }).click();

  let detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail.getByRole("button", { name: "Delete work story" })).toHaveCount(0);
  await detail.getByRole("button", { name: "Close selected work detail" }).click();
  await page.getByRole("button", { name: /US-065/ }).click();
  detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail.getByRole("button", { name: "Delete work story" })).toHaveCount(0);
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
  const longToken =
    "BoundedWorkItemCardsNeedToContainThisUnbrokenRunIdentifierFailureCategoryLaneLabelAndBlockerMetadata1234567890";
  const longReadyItem = {
    ...boardItem(`US-068-${longToken}`, `Bounded summary ${longToken} ${longToken}`, "Ready"),
    reason: `Ready because ${longToken} should stay inside the card summary instead of widening the board column.`
  };
  const longAttentionItem = {
    ...boardItem("US-968", `Needs attention ${longToken}`, "Needs Attention"),
    lane: `normal-${longToken}`,
    run_id: `run_${longToken}`,
    reason: `Failure reason ${longToken} remains a compact board summary.`,
    failure_summary: {
      category: `Category-${longToken}`,
      reason: `Reason-${longToken}`,
      latest_event: `Event-${longToken}`,
      latest_error: `Error-${longToken}`,
      run_id: `run_${longToken}`,
      evidence_artifacts: [`.harness/runs/run_${longToken}/RESULT.json`],
      next_action: `Inspect-${longToken}`
    }
  };
  const denseReadyItems = Array.from({ length: 22 }, (_, index) =>
    boardItem(`US-9${String(index).padStart(2, "0")}`, `Dense ready task ${index + 1}`, "Ready")
  );
  const sparseItems = ["Blocked", "In Progress", "Review", "Needs Attention", "Done"].map((state, index) =>
    boardItem(`US-8${index}`, `${state} task`, state)
  );

  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ items: [longReadyItem, ...denseReadyItems, longAttentionItem, ...sparseItems] })
    });
  });

  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto("/");

  for (const state of ["Ready", "Blocked", "In Progress", "Review", "Needs Attention", "Done"]) {
    await expect(page.getByRole("region", { name: `${state} column` })).toBeVisible();
  }

  const readyColumn = page.getByRole("region", { name: "Ready column" });
  const needsAttentionColumn = page.getByRole("region", { name: "Needs Attention column" });
  const readyTasks = page.locator('[aria-label="Ready tasks"]');
  const board = page.locator("#board");
  const longReadyCard = page.getByTestId("task-card").filter({ hasText: `US-068-${longToken}` });
  const longAttentionCard = page.getByTestId("task-card").filter({ hasText: "US-968" });
  const pageScrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const viewportHeight = await page.evaluate(() => window.innerHeight);
  const readyMetrics = await readyTasks.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
    scrollTop: element.scrollTop
  }));

  expect(readyMetrics.scrollHeight).toBeGreaterThan(readyMetrics.clientHeight);
  expect(pageScrollHeight).toBeLessThan(viewportHeight + 280);
  await expectPageNoHorizontalOverflow(page);
  await expectNoHorizontalOverflow(board, "desktop board");
  await expectNoHorizontalOverflow(readyColumn, "desktop ready column");
  await expectNoHorizontalOverflow(needsAttentionColumn, "desktop needs attention column");
  await expectNoHorizontalOverflow(longReadyCard, "desktop long ready card");
  await expectNoHorizontalOverflow(longAttentionCard, "desktop long needs attention card");

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
  const boardBox = await board.boundingBox();
  expect(boardBox?.y ?? 9999).toBeLessThan(760);
  const mobileReadyMetrics = await readyTasks.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight
  }));
  expect(mobileReadyMetrics.scrollHeight).toBeGreaterThan(mobileReadyMetrics.clientHeight);
  await expectPageNoHorizontalOverflow(page);
  await expectNoHorizontalOverflow(board, "mobile board");
  await expectNoHorizontalOverflow(readyColumn, "mobile ready column");
  await expectNoHorizontalOverflow(needsAttentionColumn, "mobile needs attention column");
  await expectNoHorizontalOverflow(longReadyCard, "mobile long ready card");
  await expectNoHorizontalOverflow(longAttentionCard, "mobile long needs attention card");
  await readyColumn.getByRole("button", { name: /US-900/ }).click();
  await expect(page.getByRole("dialog", { name: "Selected work detail" })).toBeVisible();
});

test("done column keeps dense completed task cards readable while scrolling internally", async ({ page }) => {
  const denseDoneItems = Array.from({ length: 48 }, (_, index) => {
    const item = boardItem(
      `US-070-D${String(index).padStart(2, "0")}`,
      `Readable Done card summary ${index + 1}`,
      "Done"
    );
    item.reason = `Completed work item ${index + 1} remains readable in a dense Done column.`;
    item.run_id = index % 2 === 0 ? `run_done_${String(index).padStart(2, "0")}` : null;
    return item;
  });

  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ items: [boardItem("US-070-R", "Ready control", "Ready"), ...denseDoneItems] })
    });
  });

  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto("/");

  const board = page.locator("#board");
  const doneColumn = page.getByRole("region", { name: "Done column" });
  const doneTasks = page.locator('[aria-label="Done tasks"]');
  const firstDoneCard = doneColumn.getByTestId("task-card").filter({ hasText: "US-070-D00" });
  const secondDoneCard = doneColumn.getByTestId("task-card").filter({ hasText: "US-070-D01" });

  await expect(firstDoneCard).toBeVisible();
  await expect(firstDoneCard).toContainText("configured");
  await expect(firstDoneCard).toContainText("Readable Done card summary 1");
  await expect(firstDoneCard).toContainText("normal");
  await expect(firstDoneCard).toContainText("run_done_00");
  await expect(secondDoneCard).toContainText("No run");
  await expectReadableTaskCard(firstDoneCard, "desktop first Done card");
  await expectReadableTaskCard(secondDoneCard, "desktop second Done card");

  const doneMetrics = await doneTasks.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
    scrollTop: element.scrollTop
  }));
  expect(doneMetrics.scrollHeight).toBeGreaterThan(doneMetrics.clientHeight);
  await expectPageNoHorizontalOverflow(page);
  await expectNoHorizontalOverflow(board, "desktop board with dense Done cards");
  await expectNoHorizontalOverflow(doneColumn, "desktop Done column");
  await expectNoHorizontalOverflow(firstDoneCard, "desktop first Done card");

  await doneTasks.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await expect(doneColumn.getByRole("heading", { name: "Done", exact: true })).toBeVisible();
  await expect(doneColumn.getByRole("button", { name: /US-070-D47/ })).toBeVisible();
  await expect
    .poll(async () => doneTasks.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(doneMetrics.scrollTop);

  await page.setViewportSize({ width: 390, height: 760 });
  await doneTasks.evaluate((element) => {
    element.scrollTop = 0;
  });
  await expect(firstDoneCard).toBeVisible();
  await expectReadableTaskCard(firstDoneCard, "mobile first Done card");
  const mobileDoneMetrics = await doneTasks.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight
  }));
  expect(mobileDoneMetrics.scrollHeight).toBeGreaterThan(mobileDoneMetrics.clientHeight);
  await expectPageNoHorizontalOverflow(page);
  await expectNoHorizontalOverflow(board, "mobile board with dense Done cards");
  await expectNoHorizontalOverflow(doneColumn, "mobile Done column");
  await expectNoHorizontalOverflow(firstDoneCard, "mobile first Done card");
});

test("active run polling refreshes terminal review and needs-attention board states", async ({ page }) => {
  let boardReads = 0;
  await page.route("**/api/board", async (route) => {
    boardReads += 1;
    const reviewItem = boardItem("US-069A", "Terminal Review Refresh", boardReads < 2 ? "In Progress" : "Review");
    reviewItem.run_id = boardReads < 2 ? "run_review_active" : "run_review_done";
    reviewItem.active_run = boardReads < 2 ? "run_review_active" : null;
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [reviewItem] }) });
  });
  await page.route("**/api/runs/run_review_done/review", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "run_review_done",
        story_id: "US-069A",
        status: "completed",
        outcome: "completed",
        summary: "Ready for review.",
        result: null,
        validation: null,
        changed_files: [],
        changeset_preview: null,
        pr_url: null,
        pr_status: "missing",
        artifact_paths: [],
        suggested_next_action: "Review terminal state.",
        failure_summary: null,
        recovery_action: null,
        events: []
      })
    });
  });

  await page.goto("/");
  await expect(page.getByRole("region", { name: "Review column" }).getByRole("button", { name: /US-069A/ })).toBeVisible({
    timeout: 5000
  });

  boardReads = 0;
  await page.route("**/api/board", async (route) => {
    boardReads += 1;
    const attentionItem = boardItem("US-069B", "Terminal Attention Refresh", boardReads < 2 ? "In Progress" : "Needs Attention");
    attentionItem.run_id = boardReads < 2 ? "run_attention_active" : "run_attention_failed";
    attentionItem.active_run = boardReads < 2 ? "run_attention_active" : null;
    attentionItem.failure_summary =
      boardReads < 2
        ? null
        : {
            category: "Codex run failure",
            reason: "Terminal failure arrived from the backend.",
            latest_event: "turn/completed",
            latest_error: "failed",
            run_id: "run_attention_failed",
            evidence_artifacts: [".harness/runs/run_attention_failed/RESULT.json"],
            next_action: "Inspect the failed run."
          };
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [attentionItem] }) });
  });
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("region", { name: "Needs Attention column" }).getByRole("button", { name: /US-069B/ })).toBeVisible({
    timeout: 5000
  });
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

test("needs attention detail keeps long failure category bounded on mobile", async ({ page }) => {
  const longToken =
    "NeedsAttentionFailureCategoryShouldWrapInsideTheMobileDetailDialogWithoutCreatingHorizontalOverflow1234567890";
  const failureSummary = {
    category: `Category-${longToken}`,
    reason: `Failure reason ${longToken}`,
    latest_event: `turn/completed-${longToken}`,
    latest_error: `error-${longToken}`,
    run_id: `run_${longToken}`,
    evidence_artifacts: [`.harness/runs/run_${longToken}/RESULT.json`],
    next_action: `Inspect ${longToken}`
  };

  await page.setViewportSize({ width: 390, height: 760 });
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            ...boardItem("US-066", `Needs Attention ${longToken}`, "Needs Attention"),
            run_id: `run_${longToken}`,
            reason: failureSummary.reason,
            failure_summary: failureSummary
          }
        ]
      })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-066/ }).click();

  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail.getByText(failureSummary.category)).toBeVisible();
  await expectNoHorizontalOverflow(page.getByTestId("task-detail-popup"), "mobile needs attention detail popup");
  await expectPageNoHorizontalOverflow(page);
});

test("execution recovery retries needs attention work and preserves failed evidence", async ({ page }) => {
  const failureSummary = {
    category: "Codex run failure",
    reason: "Codex turn failed.",
    latest_event: "turn/completed status failed",
    latest_error: "Codex turn failed.",
    run_id: "run_failed",
    evidence_artifacts: [".harness/runs/run_failed/APP_SERVER_EVENTS.jsonl"],
    next_action: "Inspect APP_SERVER_EVENTS.jsonl and retry when safe."
  };
  const recoveryAction = {
    kind: "execution_retry",
    label: "Retry work",
    endpoint: "/api/tasks/US-067/recover",
    confirmation: "Start a new Symphony run for this task? The failed run evidence stays available."
  };
  let recovered = false;

  page.on("dialog", async (dialog) => {
    expect(dialog.message()).toContain("Start a new Symphony run");
    await dialog.accept();
  });
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            ...boardItem("US-067", "Needs Attention Recovery Action", recovered ? "In Progress" : "Needs Attention"),
            run_id: recovered ? "run_recovery" : "run_failed",
            active_run: recovered ? "run_recovery" : null,
            reason: recovered ? "active run run_recovery" : failureSummary.reason,
            failure_summary: recovered ? null : failureSummary,
            recovery_action: recovered ? null : recoveryAction
          }
        ]
      })
    });
  });
  await page.route("**/api/runs/run_failed/review", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "run_failed",
        story_id: "US-067",
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
        recovery_action: recoveryAction,
        events: []
      })
    });
  });
  await page.route("**/api/tasks/US-067/recover", async (route) => {
    recovered = true;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ run_id: "run_recovery", story_id: "US-067", status: "recovering" })
    });
  });
  await page.route("**/api/runs/run_recovery/events", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "run_recovery",
        events: [
          { method: "turn/started", params: { turn: { status: "inProgress" } } },
          { method: "item/agentMessage/delta", params: { itemId: "retry_msg", delta: "Retry run is now live." } }
        ]
      })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-067/ }).click();
  const detail = page.getByRole("dialog", { name: "Selected work detail" });

  await expect(detail.getByRole("button", { name: "Retry work" })).toBeVisible();
  await detail.getByRole("button", { name: "Retry work" }).click();

  await expect(page.getByRole("button", { name: /US-067/ })).toContainText("active");
  await expect(detail.getByRole("heading", { name: "Prior failed run evidence" })).toBeVisible();
  await expect(detail.getByText(".harness/runs/run_failed/APP_SERVER_EVENTS.jsonl").first()).toBeVisible();
  await expect(detail.getByRole("heading", { name: "Run communication" })).toBeVisible();
  await expect(detail.getByText("Retry run is now live.")).toBeVisible();
});

test("review endpoint failures render explicit alert evidence", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    const item = boardItem("US-069", "Review Error State", "Review");
    item.run_id = "run_review_error";
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [item] }) });
  });
  await page.route("**/api/runs/run_review_error/review", async (route) => {
    await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: "review exploded" }) });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-069/ }).click();
  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail.getByRole("alert")).toContainText("review exploded");
  await expect(detail.getByText("run_review_error", { exact: true }).first()).toBeVisible();
});

test("pr retry recovers completed needs attention runs without rerunning work", async ({ page }) => {
  const failureSummary = {
    category: "PR creation failure",
    reason: "pull request creation failed: gh auth failed",
    latest_event: null,
    latest_error: "pull request creation failed: gh auth failed",
    run_id: "run_pr_failed",
    evidence_artifacts: [".harness/runs/run_pr_failed/SUMMARY.md"],
    next_action: "Retry pull request creation after fixing the reported PR error."
  };
  const recoveryAction = {
    kind: "pr_retry",
    label: "Retry PR creation",
    endpoint: "/api/runs/run_pr_failed/pr-retry",
    confirmation: "Retry pull request creation for this completed run?"
  };
  let prCreated = false;

  page.on("dialog", async (dialog) => {
    expect(dialog.message()).toContain("Retry pull request creation");
    await dialog.accept();
  });
  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            ...boardItem("US-067", "Needs Attention Recovery Action", prCreated ? "Review" : "Needs Attention"),
            run_id: "run_pr_failed",
            reason: prCreated ? "review pull request" : failureSummary.reason,
            failure_summary: prCreated ? null : failureSummary,
            recovery_action: prCreated ? null : recoveryAction
          }
        ]
      })
    });
  });
  await page.route("**/api/runs/run_pr_failed/review", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "run_pr_failed",
        story_id: "US-067",
        status: "completed",
        outcome: "completed",
        summary: "Completed work, PR failed.",
        result: null,
        validation: null,
        changed_files: [],
        changeset_preview: null,
        pr_url: prCreated ? "https://example.test/pr/67" : null,
        pr_status: prCreated ? "created" : "failed",
        artifact_paths: failureSummary.evidence_artifacts,
        suggested_next_action: prCreated ? "Review pull request." : failureSummary.next_action,
        failure_summary: prCreated ? null : failureSummary,
        recovery_action: prCreated ? null : recoveryAction,
        events: []
      })
    });
  });
  await page.route("**/api/runs/run_pr_failed/pr-retry", async (route) => {
    prCreated = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ run_id: "run_pr_failed", pr_status: "created", pr_url: "https://example.test/pr/67" })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-067/ }).click();
  const detail = page.getByRole("dialog", { name: "Selected work detail" });

  await expect(detail.getByRole("button", { name: "Retry PR creation" })).toBeVisible();
  await expect(detail.getByRole("button", { name: /Start/ })).toHaveCount(0);
  await detail.getByRole("button", { name: "Retry PR creation" }).click();

  await expect(detail.getByText("https://example.test/pr/67")).toBeVisible();
  await expect(detail.getByRole("button", { name: "Mark Merged" })).toBeEnabled();
});

test("artifact control is explicitly unavailable and long review values stay bounded on mobile", async ({ page }) => {
  const longToken =
    "VeryLongReviewArtifactPathChangedFileBlockerChildAndRunIdentifierThatMustWrapInsideTheMobileDialog1234567890";
  await page.setViewportSize({ width: 390, height: 760 });
  await page.route("**/api/board", async (route) => {
    const item = boardItem("US-069", `Long Review ${longToken}`, "Review");
    item.run_id = `run_${longToken}`;
    item.blockers = [`US-BLOCKER-${longToken}`];
    item.children = [`US-CHILD-${longToken}`];
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [item] }) });
  });
  await page.route(`**/api/runs/run_${longToken}/review`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: `run_${longToken}`,
        story_id: "US-069",
        status: "completed",
        outcome: "completed",
        summary: `Summary ${longToken}`,
        result: null,
        validation: { artifact: longToken },
        changed_files: [`crates/harness-symphony/web-ui/src/${longToken}.tsx`],
        changeset_preview: null,
        pr_url: null,
        pr_status: "missing",
        artifact_paths: [`.harness/runs/run_${longToken}/APP_SERVER_EVENTS.jsonl`],
        suggested_next_action: `Review long values ${longToken}`,
        failure_summary: null,
        recovery_action: null,
        events: []
      })
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /US-069/ }).click();
  const detail = page.getByRole("dialog", { name: "Selected work detail" });
  await expect(detail.getByRole("button", { name: "Open artifacts" })).toBeDisabled();
  await expect(detail.getByRole("button", { name: "Open artifacts" })).toHaveAttribute("title", /not available/);
  await expectNoHorizontalOverflow(detail, "mobile detail dialog");
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

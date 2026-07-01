import { expect, test } from "@playwright/test";

const agentsPayload = {
  agents: [
    {
      adapter: "claudecode",
      active: true,
      binary_present: true,
      binary_detail: "2.1.197 (Claude Code)",
      auth_ready: false,
      auth_detail: "no Claude Code credentials found",
      overall: "needs-setup",
      next: "Authenticate: run `claude` and log in, or set ANTHROPIC_API_KEY."
    },
    {
      adapter: "codex",
      active: false,
      binary_present: false,
      binary_detail: "codex is not runnable: not found on PATH",
      auth_ready: false,
      auth_detail: "no Codex credentials found",
      overall: "not-installed",
      next: "Install Codex CLI."
    },
    {
      adapter: "custom",
      active: false,
      binary_present: false,
      binary_detail: "no agent binary configured",
      auth_ready: true,
      auth_detail: "auth not required",
      overall: "ready",
      next: null
    }
  ]
};

test("agents strip renders a readiness badge per adapter", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });
  await page.route("**/api/agents", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(agentsPayload) });
  });

  await page.goto("/");

  const strip = page.getByRole("region", { name: "Agent readiness" });
  await expect(strip).toBeVisible();

  const claude = page.getByTestId("agent-card-claudecode");
  await expect(claude.getByText("claudecode")).toBeVisible();
  await expect(claude.getByText("active", { exact: true })).toBeVisible();
  await expect(claude.getByText("Needs setup")).toBeVisible();
  // binary detail and the next-step hint live in the pill's tooltip, keeping the strip compact.
  await expect(claude).toHaveAttribute("title", /2\.1\.197 \(Claude Code\)/);
  await expect(claude).toHaveAttribute("title", /Authenticate: run/);

  await expect(page.getByTestId("agent-card-codex").getByText("Not installed")).toBeVisible();
  await expect(page.getByTestId("agent-card-custom").getByText("Ready", { exact: true })).toBeVisible();
});

test("agents strip degrades gracefully when the endpoint fails", async ({ page }) => {
  await page.route("**/api/board", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });
  await page.route("**/api/agents", async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: "boom" })
    });
  });

  await page.goto("/");

  await expect(page.getByRole("region", { name: "Agent readiness" })).toBeVisible();
  await expect(page.getByText("Agent status unavailable.")).toBeVisible();
});

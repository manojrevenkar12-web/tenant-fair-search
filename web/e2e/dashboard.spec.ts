import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

async function accessible(page: import("@playwright/test").Page) {
  await page.waitForTimeout(700); // let entrance motion finish before contrast checks
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}

test("relevance: the hero compares one real query, and every shape can be shown", async ({ page }) => {
  await page.goto("/#/relevance");
  await expect(page.getByRole("heading", { name: "Same query, two answers" })).toBeVisible();
  const tabs = page.getByRole("tablist", { name: "Query shape" }).getByRole("tab");
  expect(await tabs.count()).toBeGreaterThan(1);
  await tabs.nth(1).click();
  await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("region", { name: "Lexical (BM25) only" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Every design on the same queries" })).toBeVisible();
  await accessible(page);
});

test("isolation and cost views read the same report", async ({ page }) => {
  await page.goto("/#/isolation");
  await expect(page.getByRole("heading", { name: /The others don't notice/ })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Other shops' p99, during the burst" })).toBeVisible();
  await accessible(page);
  await page.goto("/#/cost");
  await expect(page.getByRole("heading", { name: "What a query costs" })).toBeVisible();
  await accessible(page);
});

test("a missing report shows what to run, a broken one offers a retry, a slow one a skeleton", async ({ page }) => {
  await page.route("**/reports/dev.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/#/relevance");
  await expect(page.getByText("No evaluation yet")).toBeVisible();

  await page.unroute("**/reports/dev.json");
  await page.route("**/reports/dev.json", (r) => r.fulfill({ status: 500, body: "" }));
  await page.goto("/#/cost");
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("HTTP 500");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();

  await page.unroute("**/reports/dev.json");
  await page.route("**/reports/dev.json", async (r) => {
    await new Promise((res) => setTimeout(res, 1500));
    await r.continue();
  });
  await page.goto("/#/isolation");
  await page.reload();
  await expect(page.getByRole("status", { name: "Loading the isolation report" })).toBeVisible();
});

test("live search shows the plan and hits, an empty answer, and a failure with retry", async ({ page }) => {
  let mode: "hits" | "empty" | "down" = "hits";
  await page.route("**/v1/tenants/*/search", (r) => {
    if (mode === "down") return r.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: "search timed out" }) });
    const hits = mode === "hits" ? [{ id: "outdoor-00042", score: 0.0327 }, { id: "outdoor-00007", score: 0.0311 }] : [];
    return r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ tenant: "outdoor", design: "routed", shape: "keyword", plan: "hybrid", text: "raincoat", filters: { colour: "navy" }, hits, esTookMs: 7, costEur: 0.0000004 }),
    });
  });
  await page.goto("/#/search");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("region", { name: "Results" })).toContainText("hybrid");
  await expect(page.getByText("outdoor-00042")).toBeVisible();
  await accessible(page);

  mode = "empty";
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("No products matched")).toBeVisible();

  mode = "down";
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("search timed out");
  mode = "hits";
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByText("outdoor-00042")).toBeVisible();
});

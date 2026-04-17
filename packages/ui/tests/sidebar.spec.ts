import { test, expect } from "@playwright/test";

test.describe("sidebar-shows-health (Tier 3)", () => {
  test("renders with required locator text and matches screenshot", async ({
    page,
  }) => {
    await page.goto("/#sidebar-shows-health");
    await page.waitForSelector(".sidebar-host", { state: "attached" });

    const healthBar = page.locator('[data-testid="health-bar"]');
    await expect(healthBar).toContainText("60%");

    const firstReady = page
      .locator('[data-testid="ready-queue"] li')
      .first();
    await expect(firstReady).toContainText("Fix auth bug");

    await expect(page.locator(".sidebar-host")).toHaveScreenshot(
      "sidebar-basic.png"
    );
  });
});

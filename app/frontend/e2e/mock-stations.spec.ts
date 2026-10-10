import { expect, test } from "@playwright/test";

test("shows the mock station fixture", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("S001")).toBeVisible();
  await expect(page.getByText("Mock data")).toBeVisible();
});

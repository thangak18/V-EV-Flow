import { expect, test } from "@playwright/test";

test("map failure keeps the textual plan usable", async ({ page }) => {
  await page.route("**/goong-js@**", (route) => route.abort());
  await page.route("**/tiles.goong.io/**", (route) => route.abort());

  await page.goto("/driver");
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();
  await expect(page.getByText(/No feasible station/i)).toBeVisible();
  await expect(page.getByLabel("Station text list")).toBeVisible();
  await expect(page.getByText("Mock data").first()).toBeVisible();
});

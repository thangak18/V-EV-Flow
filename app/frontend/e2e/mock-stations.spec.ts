import { expect, test } from "@playwright/test";

test("driver shell shows mock data badge and station text list", async ({
  page,
}) => {
  await page.goto("/driver");
  await expect(page.getByText("Mock data")).toBeVisible();
  await expect(page.getByLabel("Station text list")).toBeVisible();
});

import { expect, test } from "./base";

test("operator loads pressure and compares three strategies", async ({
  page,
}) => {
  await page.goto("/operator");
  await page.getByLabel("Scenario").selectOption("tet");
  await page.getByRole("button", { name: /Apply scenario/i }).click();
  await expect(page.getByLabel("Pressure legend")).toBeVisible();
  await expect(page.getByLabel("Station text list")).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("button", { name: /Compare 3 strategies/i }).click();
  await expect(page.getByText("Nearest")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Currently available")).toBeVisible();
  await expect(page.getByText("AI allocation")).toBeVisible();
});

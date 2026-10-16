import { expect, test } from "./base";

test("Advanced cannot collapse while Battery is invalid", async ({ page }) => {
  await page.goto("/driver");

  const details = page.locator("details.driver-advanced");
  await details.locator("summary").click();
  await expect(details).toHaveAttribute("open", "");

  await page.getByLabel(/Dung lượng pin/).fill("");
  await expect(page.getByLabel(/Dung lượng pin/)).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await expect(
    page.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
  ).toBeDisabled();
  await expect(details).toHaveClass(/driver-advanced--locked/);
  await expect(details).toHaveAttribute("open", "");

  // Force-collapse via DOM (same class of bug Thắng reproduced).
  await details.evaluate((el) => {
    (el as HTMLDetailsElement).open = false;
  });
  // React controlled `open` + onToggle must restore open=true.
  await expect(details).toHaveAttribute("open", "");
  await expect(page.getByLabel(/Dung lượng pin/)).toBeVisible();
});

test("vehicle settings contain only vehicle inputs and the data clock is readonly", async ({page})=>{
  const context=await (await page.request.get('/api/runtime?scenario=normal')).json();
  await page.goto('/driver');
  const details=page.locator('details.driver-advanced');
  await details.locator('summary').click();
  await expect(details.locator('input')).toHaveCount(2);
  await expect(page.getByLabel(/Dung lượng pin/)).toBeVisible();
  await expect(page.getByLabel(/Tiêu hao/)).toBeVisible();
  await expect(page.getByLabel(/Giờ quan sát/)).toHaveCount(0);
  await expect(page.locator('.data-snapshot-note time')).toHaveAttribute('datetime',context.observed_at);
});

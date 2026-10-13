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

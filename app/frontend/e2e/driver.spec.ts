import { expect, test } from "./base";

test("driver submits once against the integrated recommend API", async ({
  page,
}) => {
  await page.goto("/driver");
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();

  await expect(page.getByTestId("plan-hero")).toBeVisible();
  await expect(page.getByText(/Trạm chính/i).first()).toBeVisible();
  await expect(page.getByText("Dữ liệu minh họa").first()).toBeVisible();
  await expect(page.getByLabel("Station text list")).toBeVisible();
});

import { expect, test } from "./base";

test("driver submits once against the Phase 0 mock recommend", async ({
  page,
}) => {
  await page.goto("/driver");
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();

  // Phase 0 mock returns null primary/backup with an explicit placeholder reason.
  await expect(page.getByText(/Không có trạm khả thi/i)).toBeVisible();
  await expect(
    page.getByText(/recommendation ranking is not implemented/i),
  ).toBeVisible();
  await expect(page.getByText("Dữ liệu mock").first()).toBeVisible();
  await expect(page.getByLabel("Station text list")).toBeVisible();
});

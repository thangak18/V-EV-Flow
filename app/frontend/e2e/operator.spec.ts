import { expect, test } from "./base";

test("operator loads pressure and compares three strategies", async ({
  page,
}) => {
  await page.goto("/operator");
  await page.getByLabel("Kịch bản nhu cầu sạc").selectOption("tet");
  await page.getByRole("button", { name: /Áp dụng kịch bản/i }).click();
  await expect(page.getByLabel("Chú thích áp lực")).toBeVisible();
  await expect(page.getByText(/Danh sách điểm trên bản đồ/i)).toBeVisible({
    timeout: 15_000,
  });
  await page.getByText(/Danh sách điểm trên bản đồ/i).click();
  await expect(page.getByLabel("Station text list")).toBeVisible();

  await page.getByRole("button", { name: /So sánh 3 chiến lược/i }).click();
  await expect(page.getByText("Gần nhất").first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("Đang trống").first()).toBeVisible();
  await expect(page.getByText("Phân bổ AI").first()).toBeVisible();
});

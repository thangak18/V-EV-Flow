import { expect, test } from "./base";

test.describe("Goong map failure fallback", () => {
  test("Goong SDK abort shows Map unavailable while text list stays usable", async ({
    page,
  }) => {
    // Routes are aborted in e2e/base.ts; build bakes VITE_GOONG_MAP_KEY so
    // this exercises GoongMapAdapter failure — not FakeMapAdapter.
    await page.goto("/driver");

    await expect(page.getByText(/Bản đồ Goong/i)).toBeVisible();
    // Must not fall back to FakeMap schematic mode for this case.
    await expect(page.getByText(/Đang dùng bản đồ schematic/i)).toHaveCount(0);
    await expect(page.getByRole("alert")).toContainText(/Bản đồ lỗi/i, {
      timeout: 20_000,
    });
    await expect(page.getByLabel("Station text list")).toBeVisible();
    await expect(page.getByLabel("Station text list")).toContainText(
      /Điểm đi/i,
    );

    // Plan UI must remain usable after map failure.
    await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();
    await expect(page.getByText(/Không có trạm khả thi/i)).toBeVisible();
    await expect(page.getByLabel("Station text list")).toBeVisible();
    await expect(page.getByText("Dữ liệu mock").first()).toBeVisible();
  });

  test("operator Goong failure still exposes pressure text list after apply", async ({
    page,
  }) => {
    await page.goto("/operator");
    // MapView mounts only after pressure AsyncState leaves idle.
    await page.getByRole("button", { name: /Áp dụng kịch bản/i }).click();
    await expect(page.getByLabel("Chú thích áp lực")).toBeVisible();

    await expect(page.getByText(/Bản đồ Goong/i)).toBeVisible();
    await expect(page.getByRole("alert")).toContainText(/Bản đồ lỗi/i, {
      timeout: 20_000,
    });
    await expect(page.getByText(/Danh sách điểm trên bản đồ/i)).toBeVisible({
      timeout: 15_000,
    });
  });
});

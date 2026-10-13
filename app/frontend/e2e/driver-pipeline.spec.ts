import { expect, test } from "./base";
import {
  EMPTY_RECOMMEND,
  PIPELINE_RECOMMEND,
  UNLOCATED_RECOMMEND,
} from "./fixtures/pipeline";

async function fulfillRecommend(
  page: import("@playwright/test").Page,
  body: unknown,
  status = 200,
) {
  await page.route("**/api/recommend", async (route) => {
    await route.fulfill({
      status,
      contentType: "application/json",
      body:
        status === 200
          ? JSON.stringify(body)
          : JSON.stringify({
              code: "upstream_unavailable",
              message: "recommend unavailable",
            }),
    });
  });
}

test.describe("driver pipeline-shaped recommend (route inject)", () => {
  test("renders primary backup ETA probability and simulated badge", async ({
    page,
  }) => {
    await fulfillRecommend(page, PIPELINE_RECOMMEND);
    await page.goto("/driver");
    await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();

    await expect(page.getByText("Dữ liệu mô phỏng").first()).toBeVisible();
    const hero = page.getByTestId("plan-hero");
    await expect(hero).toBeVisible();
    await expect(hero).toContainText("Long Dien Crossing");
    await expect(hero).toContainText("85%");
    await expect(hero).toContainText(/16:40/);
    await expect(page.getByText("Trạm dự phòng").first()).toBeVisible();
    await expect(page.getByText("Vung Tau Back Beach").first()).toBeVisible();
    await expect(page.getByText("60%").first()).toBeVisible();

    const list = page.getByLabel("Station text list");
    await expect(list).toBeVisible();
    await expect(list).toContainText("Trạm chính");
    await expect(list).toContainText("10.4800");
    await expect(list).toContainText("107.2100");
    await expect(list).toContainText("Trạm dự phòng");
    await expect(list).toContainText("10.3700");
  });

  test("shows empty plan when pipeline returns no stations", async ({
    page,
  }) => {
    await fulfillRecommend(page, EMPTY_RECOMMEND);
    await page.goto("/driver");
    await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();

    await expect(page.getByText(/Không có trạm khả thi/i)).toBeVisible();
    await expect(
      page.getByText(/Không còn trạm khả thi trong tầm pin/i),
    ).toBeVisible();
    await expect(page.getByText("Dữ liệu mô phỏng").first()).toBeVisible();
  });

  test("keeps unlocated station textual without inventing coordinates", async ({
    page,
  }) => {
    await fulfillRecommend(page, UNLOCATED_RECOMMEND);
    await page.goto("/driver");
    await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();

    await expect(page.getByText(/chưa có tọa độ/i)).toBeVisible();
    const list = page.getByLabel("Station text list");
    await expect(list).toContainText("S999");
    await expect(list).not.toContainText("10.5500");
  });

  test("surfaces recommend API errors with retry", async ({ page }) => {
    await fulfillRecommend(page, null, 503);
    await page.goto("/driver");
    await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();

    await expect(page.getByText(/recommend unavailable/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: /Thử lại/i })).toBeVisible();
  });
});

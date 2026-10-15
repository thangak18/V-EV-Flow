import { expect, test } from "@playwright/test";

const record = process.env.RECORD_DEMO === "1";
test.use({ video: record ? "on" : "off" });

test.beforeEach(async ({ page }) => {
  if (!record) {
    await page.route("**/goong-js@**", (route) => route.abort());
    await page.route("**/cdn.jsdelivr.net/npm/@goongmaps/**", (route) =>
      route.abort(),
    );
    await page.route("**/tiles.goong.io/**", (route) => route.abort());
  }
});

test("driver demo: plan, reset, empty battery and recovery", async ({
  page,
}, testInfo) => {
  test.setTimeout(120_000);
  await page.request.post("/api/reset", {
    data: { contract_version: "0.1.0" },
  });
  let recommends = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/recommend") && request.method() === "POST")
      recommends++;
  });
  await page.goto("/driver");
  await expect(
    page.getByRole("heading", { name: "Chưa tìm trạm sạc" }),
  ).toBeVisible();
  expect(recommends).toBe(0);
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/ }).click();
  await expect(page.getByTestId("plan-hero")).toBeVisible({ timeout: 60_000 });
  if (record) {
    await expect(page.locator('[title^="primary:"]')).toBeVisible({
      timeout: 20_000,
    });
    await page.screenshot({
      path: testInfo.outputPath("demo-driver.png"),
      fullPage: true,
      animations: "disabled",
    });
    await page.waitForTimeout(1800); // Readable hold for the explicitly requested backup recording.
  }
  await page.getByRole("button", { name: "Đặt lại phiên" }).click();
  await expect(page.getByText(/Đã đặt lại tải phân bổ/)).toBeVisible();
  await expect(page.getByTestId("plan-hero")).toHaveCount(0);
  expect(recommends).toBe(1);
  await page.getByLabel("Pin hiện tại (SOC %)").fill("0");
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/ }).click();
  await expect(
    page.getByText("Không có trạm khả thi cho chuyến này."),
  ).toBeVisible();
  await expect(page.getByTestId("plan-hero")).toHaveCount(0);
  if (record) await page.waitForTimeout(1500);
  await page.getByLabel("Pin hiện tại (SOC %)").fill("20");
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/ }).click();
  await expect(page.getByTestId("plan-hero")).toBeVisible({ timeout: 60_000 });
  expect(recommends).toBe(3);
  if (record) await page.waitForTimeout(2000);
});

test("operator demo: pressure then an actual same-fixture comparison", async ({
  page,
}, testInfo) => {
  test.setTimeout(120_000);
  await page.goto("/operator");
  await page
    .getByRole("combobox", { name: "Kịch bản", exact: true })
    .selectOption("tet");
  await page
    .getByRole("button", { name: "Áp dụng kịch bản", exact: true })
    .click();
  await expect(page.getByText(/Đang hiển thị .* trạm có dự báo/)).toBeVisible();
  const responsesPromise = Promise.all(
    ["nearest", "currently_available", "ai_allocation"].map((strategy) =>
      page.waitForResponse(
        (response) =>
          response.url().endsWith("/api/simulate") &&
          response.request().postDataJSON().strategy === strategy,
        { timeout: 90_000 },
      ),
    ),
  );
  await page
    .getByRole("button", { name: "So sánh 3 chiến lược", exact: true })
    .click();
  const responses = await responsesPromise;
  const results = await Promise.all(
    responses.map(async (response) => {
      expect(response.status()).toBe(200);
      return response.json();
    }),
  );
  expect(new Set(results.map((result) => result.fixture_hash)).size).toBe(1);
  await expect(page.getByTestId("strategy-delta")).toBeVisible();
  for (const result of results) {
    expect(result.scenario).toBe("tet");
    expect(result.seed).toBe(42);
    expect(result.metrics.vehicle_count).toBe(100);
    await expect(
      page
        .getByText(`${(result.metrics.success_rate * 100).toFixed(1)}%`)
        .first(),
    ).toBeVisible();
  }
  if (record) {
    await page.screenshot({
      path: testInfo.outputPath("demo-operator.png"),
      fullPage: true,
      animations: "disabled",
    });
    await page.getByText("Chi tiết mô phỏng", { exact: true }).click();
    await page.waitForTimeout(3500);
  }
});

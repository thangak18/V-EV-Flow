import { expect, test } from "@playwright/test";

test.skip(
  process.env.P1_LIVE !== "1",
  "Opt-in: trusted local release and file/model/stateful runtime required",
);
const expectedModel =
  process.env.LIVE_MODEL_VERSION ?? "lightgbm-c721ddae6c9223ad";
test.use({ video: process.env.RECORD_DEMO === "1" ? "on" : "off" });

test("live Driver uses actual TreeSHAP and reports time-shift evaluation honestly", async ({
  page,
}, testInfo) => {
  test.setTimeout(180_000);
  await page.request.post("/api/reset", {
    data: { contract_version: "0.1.0" },
  });
  await page.goto("/driver");
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/recommend") &&
      response.request().method() === "POST",
    { timeout: 120_000 },
  );
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/ }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.data_type).toBe("simulated");
  expect(result.model_version).toBe(expectedModel);
  const explanation = result.primary.explanation;
  expect(explanation.method).toBe("tree_shap");
  expect(explanation.space).toBe("raw_margin_log_odds");
  expect(explanation.features).toHaveLength(29);
  expect(
    explanation.bias +
      explanation.features.reduce(
        (sum: number, item: { contribution: number }) =>
          sum + item.contribution,
        0,
      ),
  ).toBeCloseTo(explanation.raw_score, 6);
  expect(explanation.calibrated_probability).toBe(result.primary.p_available);
  await page.getByText("Vì sao có dự báo này?", { exact: true }).click();
  await expect(page.getByTestId("shap-explanation")).toContainText(
    "không cộng trực tiếp vào % xác suất",
  );
  expect(result.time_shift_evaluated).toBe(true);
  if (result.time_shift_estimate)
    await expect(page.getByTestId("time-shift-suggestion")).toContainText(
      `muộn ${result.time_shift_estimate.minutes} phút`,
    );
  else await expect(page.getByTestId("time-shift-none")).toBeVisible();
  if (process.env.RECORD_DEMO === "1")
    await expect(page.locator('[title^="primary:"]')).toBeVisible({
      timeout: 20000,
    });
  await page.getByTestId("shap-explanation").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: testInfo.outputPath("p1-driver.png"),
    fullPage: true,
    animations: "disabled",
  });
  if (process.env.RECORD_DEMO === "1") await page.waitForTimeout(2500); // Presenter-readable backup hold.
});

test("live what-if: actual 100-vehicle added capacity and twenty shifted departures", async ({
  page,
}, testInfo) => {
  test.setTimeout(240_000);
  await page.goto("/operator");
  await page
    .getByRole("combobox", { name: "Kịch bản", exact: true })
    .selectOption("tet");
  await page
    .getByRole("button", { name: "Áp dụng kịch bản", exact: true })
    .click();
  await expect(
    page.getByText("Dữ liệu mô phỏng", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "So sánh 3 chiến lược", exact: true })
    .click();
  await expect(page.getByTestId("strategy-delta")).toBeVisible({
    timeout: 120_000,
  });
  for (const kind of ["add_ports", "shift_departures"]) {
    await page
      .getByRole("radio", {
        name:
          kind === "add_ports"
            ? /Bổ sung cổng sạc/
            : /Chuyển xe sang giờ thấp điểm/,
      })
      .check();
    const responsePromise = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/whatif") &&
        response.request().postDataJSON().change.kind === kind,
      { timeout: 180_000 },
    );
    await page.getByRole("button", { name: "So sánh trước / sau" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const result = await response.json();
    expect(result.data_type).toBe("simulated");
    expect(result.before.fixture_hash).toBe(result.after.fixture_hash);
    expect(result.before_config_hash).not.toBe(result.after_config_hash);
    expect(result.before.metrics.vehicle_count).toBe(100);
    expect(result.after.metrics.vehicle_count).toBe(100);
    expect(result.after.model_version).toBe(
      kind === "add_ports" && process.env.LIVE_CAPACITY_MODEL_VERSION
        ? process.env.LIVE_CAPACITY_MODEL_VERSION
        : expectedModel,
    );
    await expect(page.getByTestId("whatif-result")).toContainText(
      "100 xe · mã lần chạy 42",
    );
    if (kind === "shift_departures") {
      expect(result.shifted_vehicle_count).toBe(20);
      await expect(page.getByTestId("whatif-result")).toContainText(
        "Đã dịch 20 xe",
      );
    } else
      await expect(page.getByTestId("whatif-result")).toContainText(
        result.prediction_mode === "capacity_retrained"
          ? "mô hình riêng phù hợp với số cổng mới"
          : "Dự báo vẫn dùng cấu hình trạm ban đầu",
      );
    await expect(
      page
        .getByTestId("whatif-result")
        .getByText(`${(result.after.metrics.success_rate * 100).toFixed(1)}%`, {
          exact: true,
        })
        .first(),
    ).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath(`p1-${kind}.png`),
      fullPage: true,
      animations: "disabled",
    });
    if (process.env.RECORD_DEMO === "1") await page.waitForTimeout(2500); // Not a synchronization assertion.
  }
});

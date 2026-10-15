/** Opt-in real artifact/server flow: see docs/runbooks/runtime-integration.md. */
import { expect, test } from "./base";

test.skip(
  process.env.PREDICTOR_BACKEND !== "model" ||
    process.env.SIMULATION_BACKEND !== "stateful",
  "Requires trusted local model + simulated histories; no binaries in Git",
);

test("driver renders real calibrated API result and model provenance", async ({
  page,
}) => {
  const reset = await page.request.post("/api/reset", { data: {} });
  expect(reset.ok()).toBeTruthy();
  await page.goto("/driver");
  await expect(page.locator("header")).not.toContainText("Dữ liệu minh họa");
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/recommend") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/i }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.primary).not.toBeNull();
  expect(result.model_version).toMatch(/^lightgbm-/);
  expect(result.data_type).toBe("simulated");
  await expect(page.getByTestId("plan-hero")).toContainText(
    `${Math.round(result.primary.p_available * 100)}%`,
  );
  await expect(page.getByText("Dữ liệu mô phỏng").first()).toBeVisible();
  await page.screenshot({
    path: "test-results/runtime-driver.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.getByText("Chi tiết kỹ thuật", { exact: true }).click();
  await expect(
    page.getByText(`Phiên bản mô hình: ${result.model_version}`, {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Station text list")).toBeVisible();
});

test("operator displays real 100-vehicle runs for all three scenarios", async ({
  page,
}) => {
  test.setTimeout(300_000);
  await page.goto("/operator");
  const pressures: string[] = [];
  for (const scenario of ["normal", "holiday_30_4", "tet"]) {
    await page.getByLabel("Kịch bản").selectOption(scenario);
    const pressurePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/api/pressure?") &&
        response.request().method() === "GET",
    );
    await page.getByRole("button", { name: /Áp dụng kịch bản/i }).click();
    const pressure = await pressurePromise;
    expect(pressure.status()).toBe(200);
    const payload = await pressure.json();
    expect(payload.scenario).toBe(scenario);
    expect(
      payload.stations.every(
        (station: { data_type: string }) => station.data_type === "simulated",
      ),
    ).toBe(true);
    pressures.push(
      JSON.stringify(
        payload.stations.map(
          (station: { p_available: number }) => station.p_available,
        ),
      ),
    );
    await expect(page.getByText("Dữ liệu mô phỏng").first()).toBeVisible();
    const responsesPromise = Promise.all(
      ["nearest", "currently_available", "ai_allocation"].map((strategy) =>
        page.waitForResponse(
          (response) =>
            response.url().endsWith("/api/simulate") &&
            response.request().postDataJSON().strategy === strategy,
          { timeout: 240_000 },
        ),
      ),
    );
    await page.getByRole("button", { name: /So sánh 3 chiến lược/i }).click();
    const responses = await responsesPromise;
    const results = await Promise.all(
      responses.map(async (response) => {
        expect(response.status()).toBe(200);
        return response.json();
      }),
    );
    expect(new Set(results.map((result) => result.fixture_hash)).size).toBe(1);
    for (const result of results) {
      expect(result.metrics.vehicle_count).toBe(100);
      expect(result.scenario).toBe(scenario);
      expect(result.seed).toBe(42);
      expect(result.model_version).toMatch(
        result.strategy === "ai_allocation"
          ? /^lightgbm-/
          : /^simulated-baseline-v1$/,
      );
    }
    await expect(page.getByTestId("simulation-source")).toContainText(
      "simulated",
    );
    await expect(page.getByTestId("strategy-delta")).toBeVisible();
    await page.screenshot({
      path: `test-results/runtime-operator-${scenario}.png`,
      fullPage: true,
      animations: "disabled",
    });
  }
  expect(new Set(pressures).size).toBeGreaterThan(1);
});

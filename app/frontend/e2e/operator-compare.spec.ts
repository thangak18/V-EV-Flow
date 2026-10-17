import { expect, test } from "./base";
import { simulateResult } from "./fixtures/pipeline";

test("operator live simulate: 100 vehicles, three strategies, no hardcoded winner", async ({
  page,
}) => {
  await page.goto("/operator");
  await page.getByLabel("Kịch bản nhu cầu sạc").selectOption("tet");
  await page.getByRole("button", { name: /Áp dụng kịch bản/i }).click();
  await expect(page.getByLabel("Chú thích áp lực")).toBeVisible({
    timeout: 15_000,
  });

  await expect(page.getByLabel(/Số xe/i)).toHaveValue("100");
  await page.getByRole("button", { name: /So sánh 3 chiến lược/i }).click();

  await expect(page.getByText("Gần nhất").first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("Đang trống").first()).toBeVisible();
  await expect(page.getByText("Phân bổ AI").first()).toBeVisible();
  await expect(
    page.getByText(/100 xe · mã lần chạy 42/i),
  ).toBeVisible();
  await expect(
    page.getByText(/So sánh cùng nhóm xe/i),
  ).toBeVisible();

  // Phase 0 FakeSimulationRunner returns identical metrics → UI must show tie.
  await expect(page.getByTestId("strategy-delta")).toContainText(/Đồng hạng/i);
  await expect(page.getByTestId("strategy-delta")).toContainText(/Gần nhất/);
  await expect(page.getByTestId("strategy-delta")).toContainText(/Đang trống/);
  await expect(page.getByTestId("strategy-delta")).toContainText(/Phân bổ AI/);
});

test("operator compare derives leader from injected runner rates", async ({
  page,
}) => {
  const rates: Record<string, number> = {
    nearest: 0.8,
    currently_available: 0.85,
    ai_allocation: 0.92,
  };

  await page.route("**/api/simulate", async (route) => {
    const body = route.request().postDataJSON() as {
      strategy: string;
      scenario: string;
      seed: number;
      vehicle_count: number;
    };
    const rate = rates[body.strategy] ?? 0.5;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        simulateResult(
          body.strategy as
            | "nearest"
            | "currently_available"
            | "ai_allocation",
          rate,
          {
            scenario: body.scenario,
            seed: body.seed,
            vehicleCount: body.vehicle_count,
          },
        ),
      ),
    });
  });

  await page.goto("/operator");
  await page.getByRole("button", { name: /So sánh 3 chiến lược/i }).click();

  await expect(page.getByTestId("strategy-delta")).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByTestId("strategy-delta")).toContainText(/Phân bổ AI/);
  await expect(page.getByTestId("strategy-delta")).toContainText(/12\.0 điểm %/);
  await expect(page.getByText("92.0%").first()).toBeVisible();
  await expect(page.getByText("80.0%").first()).toBeVisible();
  await expect(
    page.getByText(/So sánh cùng nhóm xe/i),
  ).toBeVisible();
});

test("operator pressure badge follows simulated station data_type", async ({
  page,
}) => {
  await page.route("**/api/pressure**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        time: "2026-10-13T16:00:00+07:00",
        scenario: "tet",
        contract_version: "0.1.0",
        stations: [
          {
            station_id: "S001",
            p_available: 0.35,
            pressure_score: 0.65,
            data_type: "simulated",
          },
        ],
      }),
    });
  });

  await page.goto("/operator");
  await page.getByLabel("Kịch bản nhu cầu sạc").selectOption("tet");
  await page.getByRole("button", { name: /Áp dụng kịch bản/i }).click();
  await expect(page.getByText("Dữ liệu mô phỏng").first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/áp lực 0\.65/i)).toBeVisible();
});

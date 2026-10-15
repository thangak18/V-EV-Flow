import { expect, test } from "./base";
import { PIPELINE_RECOMMEND } from "./fixtures/pipeline";
import { explanationFixture, whatIfFixture } from "../src/test/p1Fixtures";

test("driver presents SHAP raw-score units and non-binding time-shift advice", async ({
  page,
}) => {
  await page.route("**/api/recommend", async (route) => {
    const request = route.request().postDataJSON();
    await route.fulfill({
      json: {
        ...PIPELINE_RECOMMEND,
        request_id: request.request_id,
        primary: {
          ...PIPELINE_RECOMMEND.primary,
          explanation: { ...explanationFixture, calibrated_probability: 0.85 },
        },
        time_shift: 15,
        time_shift_evaluated: true,
        time_shift_estimate: {
          minutes: 15,
          station_id: "S012",
          depart_time: "2026-10-13T16:15:00+07:00",
          eta: "2026-10-13T16:55:00+07:00",
          p_available: 0.95,
          improvement: 0.1,
          assumptions: ["Giữ snapshot hiện tại; fixture kiểm tra UI."],
        },
      },
    });
  });
  await page.goto("/driver");
  await page.getByRole("button", { name: /Tìm kế hoạch sạc/ }).click();
  await expect(page.getByTestId("time-shift-suggestion")).toContainText(
    "muộn 15 phút",
  );
  await expect(page.getByTestId("time-shift-suggestion")).toContainText(
    "chưa đổi kế hoạch hoặc ghi thêm phân bổ",
  );
  await page
    .getByText("Vì sao có xác suất này? (TreeSHAP)", { exact: true })
    .click();
  await expect(page.getByTestId("shap-explanation")).toContainText("log-odds");
  await expect(page.getByTestId("shap-explanation")).toContainText(
    "Giảm điểm -0.200",
  );
});

test("operator what-if follows current drafts, validates experiment identity and blocks empty seed", async ({
  page,
}) => {
  let observed: Record<string, unknown> | null = null;
  await page.route("**/api/whatif", async (route) => {
    const body = route.request().postDataJSON();
    observed = body;
    const make = (original: typeof whatIfFixture.before) => ({
      ...original,
      scenario: body.scenario,
      seed: body.seed,
      strategy: body.strategy,
      metrics: {
        ...original.metrics,
        vehicle_count: body.vehicle_count,
        failed_count: 0,
      },
    });
    await route.fulfill({
      json: {
        ...whatIfFixture,
        change: body.change,
        before: make(whatIfFixture.before),
        after: make(whatIfFixture.after),
      },
    });
  });
  await page.goto("/operator");
  await page.getByLabel("Seed (mầm ngẫu nhiên)").fill("91");
  await page.getByLabel("Số xe", { exact: true }).fill("50");
  const run = page.getByRole("button", { name: "So sánh trước / sau" });
  await expect(run).toBeEnabled();
  await run.click();
  await expect(page.getByTestId("whatif-result")).toContainText(
    "50 xe · seed 91",
  );
  expect(observed).toMatchObject({
    seed: 91,
    vehicle_count: 50,
    change: { kind: "add_ports", station_id: "S001", ports: 2 },
  });
  await page.getByLabel("Seed (mầm ngẫu nhiên)").fill("");
  await expect(run).toBeDisabled();
});

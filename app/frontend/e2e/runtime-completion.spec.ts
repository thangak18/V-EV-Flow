import { expect, test } from "@playwright/test";

test("Goong place selection resolves coordinates and editing invalidates the old plan", async ({
  page,
}) => {
  let releaseRuntime!: () => void;
  const capabilities = new Promise<void>((resolve) => {
    releaseRuntime = resolve;
  });
  await page.route("**/api/runtime?*", async (route) => {
    await capabilities;
    return route.fulfill({
      json: {
        clock_mode: "replay",
        scenario: "normal",
        data_type: "simulated",
        observed_at: "2026-10-13T16:00:00+07:00",
        history_start: "2026-10-01T00:00:00+07:00",
        history_end: "2026-10-13T23:55:00+07:00",
        max_horizon_minutes: 180,
        places_available: true,
        available: true,
        message: "Replay lịch sử simulated.",
        allocation_backend: "sqlite",
      },
    });
  });
  await page.route("**/api/places/search?*", (route) =>
    route.fulfill({
      json: {
        provider: "goong",
        predictions: [
          { place_id: "theatre", description: "Nhà hát Thành phố" },
        ],
      },
    }),
  );
  await page.route("**/api/places/detail?*", (route) =>
    route.fulfill({
      json: {
        provider: "goong",
        place_id: "theatre",
        label: "Nhà hát Thành phố, TP.HCM",
        lat: 10.776,
        lng: 106.704,
      },
    }),
  );
  await page.route("**/cdn.jsdelivr.net/npm/@goongmaps/**", (route) =>
    route.abort(),
  );
  await page.route("**/tiles.goong.io/**", (route) => route.abort());
  await page.goto("/driver");
  const origin = page.getByRole("combobox", { name: "Điểm đi", exact: true });
  await expect(origin).toBeDisabled();
  releaseRuntime();
  await expect(origin).toBeEnabled();
  await origin.fill("Nhà hát");
  await expect(
    page.getByRole("button", { name: "Tìm kế hoạch sạc", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("option", { name: "Nhà hát Thành phố", exact: true })
    .click();
  const request = page.waitForRequest(
    (r) => r.url().endsWith("/api/recommend") && r.method() === "POST",
  );
  await page
    .getByRole("button", { name: "Tìm kế hoạch sạc", exact: true })
    .click();
  expect((await request).postDataJSON().origin).toEqual({
    lat: 10.776,
    lng: 106.704,
  });
  await expect(page.getByTestId("plan-hero")).toBeVisible();
  await origin.fill("Chưa chọn địa điểm");
  await expect(page.getByTestId("plan-hero")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Tìm kế hoạch sạc", exact: true }),
  ).toBeDisabled();
});

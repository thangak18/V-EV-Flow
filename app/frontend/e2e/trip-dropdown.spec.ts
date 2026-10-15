import { expect, test } from "@playwright/test";

test("editable trip dropdown uses directory coordinates and blocks unselected drafts", async ({
  page,
}) => {
  await page.route("**/cdn.jsdelivr.net/npm/@goongmaps/**", (route) =>
    route.abort(),
  );
  await page.route("**/tiles.goong.io/**", (route) => route.abort());
  const response = await page.request.get("/api/stations");
  const { stations } = await response.json();
  const station = stations[0];
  const label = `${station.name} (${station.station_id})`;
  await page.goto("/driver");
  const origin = page.getByRole("combobox", { name: "Điểm đi", exact: true });
  const destination = page.getByRole("combobox", {
    name: "Điểm đến",
    exact: true,
  });
  const submit = page.getByRole("button", {
    name: "Tìm kế hoạch sạc",
    exact: true,
  });
  await expect(page.locator("#trip-locations option")).not.toHaveCount(2);
  await origin.fill("địa điểm chưa chọn");
  await expect(submit).toBeDisabled();
  await origin.fill(label);
  await destination.fill(label);
  await expect(submit).toBeDisabled();
  await destination.fill("Vũng Tàu");
  const requestPromise = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/recommend") && request.method() === "POST",
  );
  await submit.click();
  const request = await requestPromise;
  expect(request.postDataJSON()).toMatchObject({
    origin: { lat: station.lat, lng: station.lng },
    destination: { lat: 10.35, lng: 107.08 },
  });
  await expect(page.getByTestId("plan-hero")).toBeVisible();
  await origin.fill("");
  await expect(page.getByTestId("plan-hero")).toHaveCount(0);
  await expect(submit).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

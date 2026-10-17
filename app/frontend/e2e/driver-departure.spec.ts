import { expect, test } from "./base";
import { PIPELINE_RECOMMEND } from "./fixtures/pipeline";

test("departure time changes the request without changing its data snapshot", async ({
  page,
}) => {
  const requests: {
    observed_at: string;
    depart_time: string;
    request_id: string;
  }[] = [];
  await page.route("**/api/recommend", (route) => {
    requests.push(route.request().postDataJSON());
    return route.fulfill({ json: PIPELINE_RECOMMEND });
  });
  const clock = (
    await (await page.request.get("/api/runtime?scenario=normal")).json()
  ).observed_at;
  await page.goto("/driver");
  const find = page.getByRole("button", {
    name: "Tìm kế hoạch sạc",
    exact: true,
  });
  await find.click();
  await expect(page.getByTestId("plan-hero")).toBeVisible();
  await page
    .getByLabel("Giờ khởi hành", { exact: true })
    .fill("2026-10-13T16:30");
  await expect(page.getByTestId("plan-hero")).toHaveCount(0);
  expect(requests).toHaveLength(1);
  await find.click();
  await expect(page.getByTestId("plan-hero")).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[1]?.observed_at).toBe(clock);
  expect(requests[1]?.depart_time).toBe("2026-10-13T16:30:00+07:00");
  expect(requests[1]?.request_id).not.toBe(requests[0]?.request_id);
  await page
    .getByLabel("Giờ khởi hành", { exact: true })
    .fill("2026-10-13T15:59");
  await expect(find).toBeDisabled();
  await expect(page.locator(".driver-toolbar").getByRole("alert")).toContainText("sớm hơn");
});

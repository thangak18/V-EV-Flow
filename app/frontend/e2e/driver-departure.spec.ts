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
  await expect(
    page.locator(".driver-toolbar").getByRole("alert"),
  ).toContainText("sớm hơn");
});

test("historical replay supports 20h with a matching snapshot and aligned form rows", async ({
  page,
}) => {
  const runtime = await (
    await page.request.get("/api/runtime?scenario=normal")
  ).json();
  await page.route("**/api/runtime?**", (route) =>
    route.fulfill({
      json: {
        ...runtime,
        clock_mode: "replay",
        data_type: "simulated",
        history_start: "2026-09-30T00:00:00+07:00",
        history_end: "2026-10-13T23:55:00+07:00",
        max_horizon_minutes: 180,
      },
    }),
  );
  let sent: { observed_at: string; depart_time: string } | undefined;
  await page.route("**/api/recommend", (route) => {
    sent = route.request().postDataJSON();
    return route.fulfill({
      json: {
        ...PIPELINE_RECOMMEND,
        primary: {
          ...PIPELINE_RECOMMEND.primary,
          eta: "2026-10-13T20:40:00+07:00",
        },
        backup: null,
      },
    });
  });
  await page.goto("/driver");
  await page
    .getByLabel("Giờ khởi hành", { exact: true })
    .fill("2026-10-13T20:02");
  const find = page.getByRole("button", {
    name: "Tìm kế hoạch sạc",
    exact: true,
  });
  await expect(find).toBeEnabled();
  await find.click();
  await expect(page.getByTestId("plan-hero")).toBeVisible();
  expect(sent).toMatchObject({
    observed_at: "2026-10-13T20:00:00+07:00",
    depart_time: "2026-10-13T20:02:00+07:00",
  });
  await expect(page.locator(".data-snapshot-note time")).toHaveAttribute(
    "datetime",
    sent!.observed_at,
  );
  const fields = await page
    .locator(".driver-toolbar__fields > .field-chip")
    .evaluateAll((nodes) =>
      nodes.map((node) => {
        const box = node.getBoundingClientRect();
        return { x: box.x, width: box.width };
      }),
    );
  expect(fields).toHaveLength(6);
  for (let i = 0; i < 3; i++) {
    expect(Math.abs(fields[i]!.x - fields[i + 3]!.x)).toBeLessThan(1);
    expect(Math.abs(fields[i]!.width - fields[i + 3]!.width)).toBeLessThan(1);
  }
});

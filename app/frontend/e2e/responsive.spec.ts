import { expect, test } from "./base";

test.describe("responsive shells", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("phone width keeps brand nav and operator controls usable", async ({
    page,
  }) => {
    await page.goto("/operator");

    await expect(page.getByRole("heading", { name: "V-EV Flow" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Driver" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Operator" })).toBeVisible();

    const frame = page.locator(".app-frame");
    await expect(frame).toBeVisible();
    const frameBox = await frame.boundingBox();
    expect(frameBox).toBeTruthy();
    expect(frameBox!.width).toBeLessThanOrEqual(390);

    const time = page.getByLabel(/Time/i);
    await expect(time).toBeVisible();
    const timeBox = await time.boundingBox();
    expect(timeBox).toBeTruthy();
    expect(timeBox!.width).toBeLessThanOrEqual(frameBox!.width);

    await expect(
      page.getByRole("button", { name: /Apply scenario/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Compare 3 strategies/i }),
    ).toBeVisible();
  });

  test("driver phone shell keeps form column and map text list", async ({
    page,
  }) => {
    await page.goto("/driver");
    await expect(page.getByRole("heading", { name: "V-EV Flow" })).toBeVisible();
    await expect(page.getByLabel("SOC %")).toBeVisible();
    await expect(page.getByLabel("Station text list")).toBeVisible();

    const panel = page.locator(".driver-panel");
    const box = await panel.boundingBox();
    expect(box).toBeTruthy();
    expect(box!.width).toBeLessThanOrEqual(390);
  });
});

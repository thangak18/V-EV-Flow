import { expect, test } from "./base";

test.describe("operator map width on tablet", () => {
  test.use({ viewport: { width: 768, height: 900 } });

  test("map-panel fills operator-map width", async ({ page }) => {
    await page.goto("/operator");
    await page.getByRole("button", { name: /Áp dụng kịch bản/i }).click();
    await expect(page.locator(".operator-map-card .map-panel")).toBeVisible({
      timeout: 30_000,
    });

    const widths = await page.evaluate(() => {
      const map = document.querySelector(".operator-map-card");
      const panel = document.querySelector(".operator-map-card .map-panel");
      return {
        map: map?.getBoundingClientRect().width ?? 0,
        panel: panel?.getBoundingClientRect().width ?? 0,
      };
    });

    expect(widths.map).toBeGreaterThan(500);
    expect(widths.panel).toBeGreaterThan(500);
    expect(Math.abs(widths.map - widths.panel)).toBeLessThan(48);
  });
});

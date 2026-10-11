import { expect, test } from "./base";

async function assertNoDocumentHorizontalOverflow(page: {
  evaluate: (fn: () => { scrollWidth: number; innerWidth: number }) => Promise<{
    scrollWidth: number;
    innerWidth: number;
  }>;
}) {
  const dims = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(
    dims.scrollWidth,
    `document scrollWidth ${dims.scrollWidth} > innerWidth ${dims.innerWidth}`,
  ).toBeLessThanOrEqual(dims.innerWidth + 1);
}

for (const width of [375, 390] as const) {
  test.describe(`operator phone ${width}px`, () => {
    test.use({ viewport: { width, height: 844 } });

    test("after Compare, page does not grow past viewport width", async ({
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
      expect(frameBox!.width).toBeLessThanOrEqual(width);

      const header = page.locator(".operator-header");
      const headerBox = await header.boundingBox();
      expect(headerBox).toBeTruthy();
      // Title + badge only — no tall empty flex-basis gap in column layout.
      expect(headerBox!.height).toBeLessThan(140);

      await page.getByRole("button", { name: /Compare 3 strategies/i }).click();
      await expect(page.getByText("Nearest")).toBeVisible({ timeout: 30_000 });
      await expect(page.locator(".table-wrap")).toBeVisible();

      await assertNoDocumentHorizontalOverflow(page);

      const wrapBox = await page.locator(".table-wrap").boundingBox();
      expect(wrapBox).toBeTruthy();
      expect(wrapBox!.width).toBeLessThanOrEqual(width);
    });

    test("seed/vehicles empty draft blocks Compare; seed 0 is allowed", async ({
      page,
    }) => {
      await page.goto("/operator");

      const seed = page.getByLabel("Seed");
      const vehicles = page.getByLabel("Vehicles");
      const compare = page.getByRole("button", {
        name: /Compare 3 strategies/i,
      });

      await seed.fill("");
      await vehicles.fill("");
      await expect(seed).toHaveValue("");
      await expect(vehicles).toHaveValue("");
      await expect(compare).toBeDisabled();
      await expect(
        page.getByText(/Empty fields are not submitted/i),
      ).toBeVisible();

      await seed.fill("0");
      await vehicles.fill("100");
      await expect(compare).toBeEnabled();
      await compare.click();
      await expect(page.getByText(/seed 0/i)).toBeVisible({ timeout: 30_000 });
    });
  });
}

test.describe("operator error row on phone", () => {
  test.use({ viewport: { width: 375, height: 844 } });

  test("failed strategy row stays inside viewport width", async ({ page }) => {
    await page.route("**/api/simulate", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          code: "upstream_unavailable",
          message: "simulator down",
        }),
      });
    });

    await page.goto("/operator");
    await page.getByRole("button", { name: /Compare 3 strategies/i }).click();
    await expect(page.getByText(/Failed:/i).first()).toBeVisible({
      timeout: 30_000,
    });
    await assertNoDocumentHorizontalOverflow(page);
  });
});

test.describe("driver phone shell", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("keeps form column and map text list", async ({ page }) => {
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

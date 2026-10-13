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

      await expect(
        page.getByRole("heading", { name: "V-EV Flow" }),
      ).toBeVisible();
      await expect(page.getByRole("link", { name: "Tài xế" })).toBeVisible();
      await expect(page.getByRole("link", { name: "Điều hành" })).toBeVisible();

      const frame = page.locator(".app-frame");
      await expect(frame).toBeVisible();
      const frameBox = await frame.boundingBox();
      expect(frameBox).toBeTruthy();
      expect(frameBox!.width).toBeLessThanOrEqual(width);

      const header = page.locator(".operator-header");
      const headerBox = await header.boundingBox();
      expect(headerBox).toBeTruthy();
      // Title + badge only — no tall empty flex-basis gap (~232px) in column layout.
      expect(headerBox!.height).toBeLessThan(170);

      await page.getByRole("button", { name: /So sánh 3 chiến lược/i }).click();
      await expect(page.getByText("Gần nhất").first()).toBeVisible({
        timeout: 30_000,
      });
      await expect(page.getByTestId("strategy-delta")).toBeVisible();

      await assertNoDocumentHorizontalOverflow(page);

      const wrapBox = await page.getByTestId("strategy-delta").boundingBox();
      expect(wrapBox).toBeTruthy();
      expect(wrapBox!.width).toBeLessThanOrEqual(width);
    });

    test("seed/vehicles empty draft blocks Compare; seed 0 is allowed", async ({
      page,
    }) => {
      await page.goto("/operator");

      const seed = page.getByLabel(/Seed/);
      const vehicles = page.getByLabel(/Số xe/);
      const compare = page.getByRole("button", {
        name: /So sánh 3 chiến lược/i,
      });

      await seed.fill("");
      await vehicles.fill("");
      await expect(seed).toHaveValue("");
      await expect(vehicles).toHaveValue("");
      await expect(compare).toBeDisabled();
      await expect(page.getByText("Seed phải là số nguyên")).toBeVisible();
      await expect(
        page.getByText("Số xe phải là số nguyên lớn hơn hoặc bằng 1"),
      ).toBeVisible();

      await seed.fill("0");
      await vehicles.fill("100");
      await expect(compare).toBeEnabled();
      await compare.click();
      await expect(page.getByText(/seed 0/i)).toBeVisible({ timeout: 30_000 });
    });

    test("decimal seed/vehicles drafts stay visible and block Compare", async ({
      page,
    }) => {
      await page.goto("/operator");

      const seed = page.getByLabel(/Seed/);
      const vehicles = page.getByLabel(/Số xe/);
      const compare = page.getByRole("button", {
        name: /So sánh 3 chiến lược/i,
      });

      await seed.fill("");
      await seed.pressSequentially("1.5");
      await expect(seed).toHaveValue("1.5");
      await expect(page.getByText("Seed phải là số nguyên")).toBeVisible();
      await expect(compare).toBeDisabled();

      await vehicles.fill("");
      await vehicles.pressSequentially("1,5");
      await expect(vehicles).toHaveValue("1,5");
      await expect(
        page.getByText("Số xe phải là số nguyên lớn hơn hoặc bằng 1"),
      ).toBeVisible();
      await expect(compare).toBeDisabled();

      await seed.fill("15");
      await vehicles.fill("15");
      await expect(page.getByText("Seed phải là số nguyên")).toHaveCount(0);
      await expect(
        page.getByText("Số xe phải là số nguyên lớn hơn hoặc bằng 1"),
      ).toHaveCount(0);
      await expect(compare).toBeEnabled();
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
    await page.getByRole("button", { name: /So sánh 3 chiến lược/i }).click();
    await expect(page.getByText(/Lỗi:/i).first()).toBeVisible({
      timeout: 30_000,
    });
    await assertNoDocumentHorizontalOverflow(page);
  });
});

test.describe("driver phone shell", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("keeps form column and map text list", async ({ page }) => {
    await page.goto("/driver");
    await expect(
      page.getByRole("heading", { name: "V-EV Flow" }),
    ).toBeVisible();
    await expect(page.getByLabel(/SOC %/)).toBeVisible();
    await expect(page.getByLabel("Station text list")).toBeVisible();

    const pageBox = await page.locator(".driver-page").boundingBox();
    expect(pageBox).toBeTruthy();
    expect(pageBox!.width).toBeLessThanOrEqual(390);
  });
});

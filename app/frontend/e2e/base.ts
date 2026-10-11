import { expect, test as base } from "@playwright/test";

/**
 * Production preview is built with a fake Goong key so MapView selects
 * GoongMapAdapter. Abort CDN/tiles by default so non-map specs stay fast
 * and deterministic when the SDK cannot load.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route("**/goong-js@**", (route) => route.abort());
    await page.route("**/cdn.jsdelivr.net/npm/@goongmaps/**", (route) =>
      route.abort(),
    );
    await page.route("**/tiles.goong.io/**", (route) => route.abort());
    await use(page);
  },
});

export { expect };

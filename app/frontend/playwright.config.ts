import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  use: { baseURL: "http://127.0.0.1:4173", trace: "on-first-retry" },
  webServer: [
    { command: "cd ../.. && uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000", url: "http://127.0.0.1:8000/api/health", reuseExistingServer: false, timeout: 120_000 },
    { command: "npm run dev -- --host 127.0.0.1 --port 4173 --strictPort", url: "http://127.0.0.1:4173", reuseExistingServer: false, timeout: 120_000 },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

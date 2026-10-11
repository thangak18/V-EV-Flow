import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const python =
  process.platform === "win32"
    ? path.join(root, ".venv", "Scripts", "python.exe")
    : path.join(root, ".venv", "bin", "python");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  use: { baseURL: "http://127.0.0.1:4173", trace: "on-first-retry" },
  webServer: [
    {
      command: `"${python}" -m uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000`,
      cwd: root,
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      // Production smoke: build then preview (not Vite HMR/dev).
      // Invoke local binaries via node so Windows PATH need not include tsc/vite.
      // Force relative /api so preview proxy works (avoids CORS vs :8000).
      command:
        "node ./node_modules/typescript/bin/tsc -b && node ./node_modules/vite/bin/vite.js build && node ./node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4173",
      url: "http://127.0.0.1:4173",
      // Always rebuild so VITE_GOONG_MAP_KEY is baked for Goong-failure e2e.
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        ...process.env,
        VITE_API_BASE_URL: "/api",
        // Fake key forces GoongMapAdapter (not FakeMap) in production preview.
        VITE_GOONG_MAP_KEY: "e2e-fake-goong-key",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

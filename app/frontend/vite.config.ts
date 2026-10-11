import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

export default defineConfig({
  plugins: [react()],
  // Read VITE_* from repo-root .env (same place as .env.example).
  envDir: repoRoot,
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  // Same proxy for `vite preview` / Playwright production smoke on :4173.
  preview: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    exclude: ["e2e/**", "node_modules/**"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/main.tsx",
        "src/types/**",
        "src/test/**",
        "src/components/map/GoongMapAdapter.ts",
        "**/*.test.{ts,tsx}",
      ],
      thresholds: {
        branches: 75,
        functions: 75,
        lines: 75,
        statements: 75,
      },
    },
  },
});

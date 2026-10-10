import { expect, test, vi } from "vitest";

import { ApiClient, ApiError } from "./api";

test("listStations returns the typed payload", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ stations: [], data_type: "mock", source_notes: [] }),
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  expect((await client.listStations()).data_type).toBe("mock");
});

test("request exposes the status and body for failed responses", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: false,
    status: 503,
    json: async () => ({ code: "unavailable", message: "Service unavailable" }),
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await expect(client.listStations()).rejects.toEqual(
    new ApiError(503, { code: "unavailable", message: "Service unavailable" }),
  );
});

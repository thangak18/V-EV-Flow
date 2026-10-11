import { expect, test, vi } from "vitest";

import { ApiClient, ApiError } from "./api";

test("listStations returns the typed payload", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    text: async () =>
      JSON.stringify({ stations: [], data_type: "mock", source_notes: [] }),
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  expect((await client.listStations()).data_type).toBe("mock");
});

test("listStations forwards an abort signal to the fetch boundary", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    text: async () =>
      JSON.stringify({ stations: [], data_type: "mock", source_notes: [] }),
  });
  const controller = new AbortController();
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await client.listStations(controller.signal);

  expect(fetcher).toHaveBeenCalledWith("http://test/api/stations", {
    method: undefined,
    headers: undefined,
    body: undefined,
    signal: controller.signal,
  });
});

test("request rejects a non-JSON success response", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "text/plain" }),
    text: async () => "Unexpected response",
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await expect(client.listStations()).rejects.toMatchObject({
    status: 200,
    code: "invalid_response",
    message: "Response body was not valid JSON",
  });
});

test("client sends every contract operation through the shared request boundary", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    text: async () => JSON.stringify({}),
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await client.predict({} as Parameters<ApiClient["predict"]>[0]);
  await client.recommend({} as Parameters<ApiClient["recommend"]>[0]);
  await client.pressure({ scenario: "normal", time: "2026-10-11T00:00:00Z" });
  await client.simulate({} as Parameters<ApiClient["simulate"]>[0]);
  await client.reset({} as Parameters<ApiClient["reset"]>[0]);

  expect(fetcher.mock.calls.map(([url]) => url)).toEqual([
    "http://test/api/predict",
    "http://test/api/recommend",
    "http://test/api/pressure?scenario=normal&time=2026-10-11T00%3A00%3A00Z",
    "http://test/api/simulate",
    "http://test/api/reset",
  ]);
});

test("request normalizes a structured error response", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: false,
    status: 503,
    headers: new Headers({ "content-type": "application/json" }),
    text: async () =>
      JSON.stringify({
        code: "unavailable",
        message: "Service unavailable",
        details: { retry_after: 60 },
      }),
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await expect(client.listStations()).rejects.toMatchObject(
    new ApiError(503, "unavailable", "Service unavailable", {
      retry_after: 60,
    }),
  );
});

test("request converts an empty error response into an ApiError", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: false,
    status: 502,
    headers: new Headers(),
    text: async () => "",
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await expect(client.listStations()).rejects.toMatchObject({
    status: 502,
    code: "http_error",
    message: "Request failed with status 502",
    details: null,
  });
});

test("request converts a non-JSON error response into an ApiError", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: false,
    status: 504,
    headers: new Headers({ "content-type": "text/plain" }),
    text: async () => "Gateway timed out",
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await expect(client.listStations()).rejects.toMatchObject({
    status: 504,
    code: "http_error",
    message: "Gateway timed out",
    details: null,
  });
});

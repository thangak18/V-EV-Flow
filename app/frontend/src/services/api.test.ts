import { expect, test, vi } from "vitest";

import { FIXTURE_HASH } from "../test/fixtureHash";
import { ApiClient, ApiError } from "./api";

function mockFetch(status: number, body: unknown, ok = status < 400) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    text: async () => JSON.stringify(body),
  });
}

const validRecommend = {
  request_id: "demo-001",
  origin: { lat: 10.78, lng: 106.7 },
  destination: { lat: 10.35, lng: 107.08 },
  observed_at: "2026-10-13T16:00:00+07:00",
  depart_time: "2026-10-13T16:00:00+07:00",
  scenario: "normal" as const,
  vehicle: {
    soc_pct: 20,
    battery_kwh: 60,
    consumption_kwh_per_km: 0.18,
    connector_type: "CCS2",
  },
};

test("listStations returns the typed payload", async () => {
  const fetcher = mockFetch(200, {
    stations: [],
    data_type: "mock",
    source_notes: [],
  });
  const client = new ApiClient("http://test/api/", fetcher as typeof fetch);

  expect((await client.listStations()).data_type).toBe("mock");
  expect(fetcher).toHaveBeenCalledWith(
    "http://test/api/stations",
    expect.objectContaining({ signal: undefined }),
  );
});

test("listStations forwards an abort signal to the fetch boundary", async () => {
  const fetcher = mockFetch(200, {
    stations: [],
    data_type: "mock",
    source_notes: [],
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

test("maps a business error without losing code", async () => {
  const fetcher = mockFetch(
    409,
    { code: "REQUEST_ID_CONFLICT", message: "conflict", details: {} },
    false,
  );
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).recommend(validRecommend),
  ).rejects.toMatchObject({
    status: 409,
    code: "REQUEST_ID_CONFLICT",
  });
});

test("maps FastAPI 422 validation errors", async () => {
  const fetcher = mockFetch(
    422,
    {
      detail: [
        { loc: ["body", "soc_pct"], msg: "too low", type: "value_error" },
      ],
    },
    false,
  );
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).recommend(validRecommend),
  ).rejects.toMatchObject({
    status: 422,
    code: "VALIDATION_ERROR",
    message: "soc_pct: too low",
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
    status: 502,
    code: "INVALID_API_RESPONSE",
  });
});

test("client sends every contract operation through the shared request boundary", async () => {
  const fetcher = vi.fn().mockImplementation(async (url: string) => {
    let body: unknown = { data_type: "mock" };
    if (String(url).includes("/stations")) {
      body = { stations: [], data_type: "mock", source_notes: [] };
    } else if (String(url).includes("/predict")) {
      body = {
        station_id: "S001",
        eta: "2026-10-13T16:40:00+07:00",
        p_available: 0.5,
        reasons: ["ok"],
        explanation_method: "rule",
        model_version: "v",
        data_type: "mock",
        contract_version: "0.1.0",
      };
    } else if (String(url).includes("/recommend")) {
      body = {
        request_id: "x",
        data_type: "mock",
        primary: null,
        backup: null,
        reasons: [],
        model_version: "v",
        allocation_method: "m",
        contract_version: "0.1.0",
      };
    } else if (String(url).includes("/pressure")) {
      body = {
        scenario: "normal",
        time: "2026-10-11T00:00:00Z",
        stations: [],
        contract_version: "0.1.0",
      };
    } else if (String(url).includes("/simulate")) {
      body = {
        strategy: "nearest",
        metrics: {
          success_rate: 1,
          mean_detour_km: 0,
          mean_wait_minutes: 0,
          failed_count: 0,
          vehicle_count: 1,
        },
        scenario: "normal",
        seed: 1,
        model_version: "v",
        fixture_hash: FIXTURE_HASH,
        contract_version: "0.1.0",
      };
    } else if (String(url).includes("/reset")) {
      body = { reset: true, contract_version: "0.1.0" };
    }
    return {
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      text: async () => JSON.stringify(body),
    };
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);

  await client.predict({
    station_id: "S001",
    observed_at: "2026-10-13T16:00:00+07:00",
    eta: "2026-10-13T16:40:00+07:00",
    connector_type: "CCS2",
    scenario: "normal",
  });
  await client.recommend(validRecommend);
  await client.getPressure({
    scenario: "normal",
    time: "2026-10-11T00:00:00Z",
  });
  await client.simulate({
    scenario: "normal",
    seed: 42,
    vehicle_count: 100,
    strategy: "nearest",
    contract_version: "0.1.0",
  });
  await client.reset({ contract_version: "0.1.0" });

  expect(fetcher.mock.calls.map(([url]) => url)).toEqual([
    "http://test/api/predict",
    "http://test/api/recommend",
    "http://test/api/pressure?scenario=normal&time=2026-10-11T00%3A00%3A00Z",
    "http://test/api/simulate",
    "http://test/api/reset",
  ]);
});

test("request normalizes a structured error response", async () => {
  const fetcher = mockFetch(
    503,
    {
      code: "unavailable",
      message: "Service unavailable",
      details: { retry_after: 60 },
    },
    false,
  );
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

test("network failures become ApiError NETWORK_ERROR", async () => {
  const fetcher = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).listStations(),
  ).rejects.toMatchObject({
    status: 0,
    code: "NETWORK_ERROR",
  });
});

test("abort errors are rethrown", async () => {
  const abortError = new DOMException("Aborted", "AbortError");
  const fetcher = vi.fn().mockRejectedValue(abortError);
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).listStations(),
  ).rejects.toBe(abortError);
});

test("rejects malformed success payloads missing discriminants", async () => {
  const fetcher = mockFetch(200, { stations: [] });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).listStations(),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects stations missing required nested fields", async () => {
  const fetcher = mockFetch(200, {
    data_type: "mock",
    source_notes: [],
    stations: [{ station_id: "S1" }],
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).listStations(),
  ).rejects.toMatchObject({
    code: "INVALID_API_RESPONSE",
    message: /listStations failed contract validation/,
  });
});

test("rejects recommend payloads with invalid nested plan probability", async () => {
  const fetcher = mockFetch(200, {
    request_id: "x",
    data_type: "mock",
    primary: {
      station_id: "S1",
      eta: "2026-10-13T16:40:00+07:00",
      distance_km: 1,
      detour_km: 0,
      arrival_soc_pct: 20,
      p_available: 1.5,
    },
    backup: null,
    reasons: [],
    model_version: "v",
    allocation_method: "m",
    contract_version: "0.1.0",
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).recommend(validRecommend),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects pressure stations missing nested fields", async () => {
  const fetcher = mockFetch(200, {
    time: "2026-10-13T16:00:00+07:00",
    scenario: "normal",
    stations: [{ station_id: "S1", p_available: 0.5 }],
    contract_version: "0.1.0",
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).getPressure({
      scenario: "normal",
      time: "2026-10-13T16:00:00+07:00",
    }),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects simulate payloads with incomplete metrics", async () => {
  const fetcher = mockFetch(200, {
    scenario: "normal",
    seed: 1,
    strategy: "nearest",
    model_version: "v",
    metrics: { success_rate: 1 },
    fixture_hash: "h",
    contract_version: "0.1.0",
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).simulate({
      scenario: "normal",
      seed: 1,
      vehicle_count: 10,
      strategy: "nearest",
      contract_version: "0.1.0",
    }),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects predict payloads missing nested discriminants", async () => {
  const fetcher = mockFetch(200, {
    station_id: "S001",
    eta: "2026-10-13T16:40:00+07:00",
    p_available: 0.5,
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).predict({
      station_id: "S001",
      observed_at: "2026-10-13T16:00:00+07:00",
      eta: "2026-10-13T16:40:00+07:00",
      connector_type: "CCS2",
      scenario: "normal",
    }),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects station lat out of range and empty connector_types", async () => {
  const fetcher = mockFetch(200, {
    data_type: "mock",
    source_notes: [],
    stations: [
      {
        station_id: "S1",
        name: "Bad",
        lat: 999,
        lng: 106.7,
        n_ports: 1,
        power_kw: 50,
        connector_types: [],
        network: "n",
        station_type: "urban",
        source: "s",
        assumptions: [],
      },
    ],
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).listStations(),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects pressure_score outside 0..1 and naive timestamps", async () => {
  const fetcher = mockFetch(200, {
    time: "2026-10-13T16:00:00",
    scenario: "normal",
    stations: [
      {
        station_id: "S1",
        p_available: 0.5,
        pressure_score: 8,
        data_type: "mock",
      },
    ],
    contract_version: "0.1.0",
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).getPressure({
      scenario: "normal",
      time: "2026-10-13T16:00:00+07:00",
    }),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects plan with negative distance and impossible arrival SOC", async () => {
  const fetcher = mockFetch(200, {
    request_id: "x",
    data_type: "mock",
    primary: {
      station_id: "S1",
      eta: "2026-10-13T16:40:00+07:00",
      distance_km: -20,
      detour_km: 0,
      arrival_soc_pct: 250,
      p_available: 0.5,
    },
    backup: null,
    reasons: [],
    model_version: "v",
    allocation_method: "m",
    contract_version: "0.1.0",
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).recommend(validRecommend),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects simulate metrics that violate backend ranges and hash format", async () => {
  const fetcher = mockFetch(200, {
    scenario: "normal",
    seed: 1,
    strategy: "nearest",
    model_version: "v",
    metrics: {
      success_rate: 4,
      mean_detour_km: 0,
      mean_wait_minutes: 0,
      failed_count: 5,
      vehicle_count: 2,
    },
    fixture_hash: "not-a-sha256",
    contract_version: "0.1.0",
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).simulate({
      scenario: "normal",
      seed: 1,
      vehicle_count: 10,
      strategy: "nearest",
      contract_version: "0.1.0",
    }),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("rejects unknown fields because schemas are strict", async () => {
  const fetcher = mockFetch(200, {
    stations: [],
    data_type: "mock",
    source_notes: [],
    unexpected: true,
  });
  await expect(
    new ApiClient("/api", fetcher as typeof fetch).listStations(),
  ).rejects.toMatchObject({ code: "INVALID_API_RESPONSE" });
});

test("ready validates adapter modes from the existing readiness endpoint", async () => {
  const fetcher = mockFetch(200, {
    ready: true,
    data_backend: "file",
    predictor_backend: "model",
    route_backend: "goong",
  });
  const client = new ApiClient("/api", fetcher as typeof fetch);
  expect((await client.ready()).route_backend).toBe("goong");
  expect(fetcher).toHaveBeenCalledWith(
    "/api/ready",
    expect.objectContaining({ method: undefined }),
  );
});

test("ready rejects incompatible response fields", async () => {
  const client = new ApiClient(
    "/api",
    mockFetch(200, { ready: true, route_backend: "unknown" }) as typeof fetch,
  );
  await expect(client.ready()).rejects.toMatchObject({
    code: "INVALID_API_RESPONSE",
  });
});

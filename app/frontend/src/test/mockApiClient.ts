import { vi } from "vitest";

import { ApiClient } from "../services/api";

export function createMockApiClient(
  overrides: Partial<ApiClient> = {},
): ApiClient {
  return {
    runtime: vi.fn().mockImplementation(async (scenario) => ({
      clock_mode: "mock",
      scenario,
      data_type: "mock",
      observed_at: "2026-10-13T16:00:00+07:00",
      history_start: null,
      history_end: null,
      max_horizon_minutes: 60,
      places_available: false,
      available: true,
      message: "Dữ liệu minh họa.",
      allocation_backend: "memory",
    })),
    ready: vi.fn().mockResolvedValue({
      ready: true,
      data_backend: "mock",
      predictor_backend: "fake",
      route_backend: "fake",
    }),
    listStations: vi.fn().mockResolvedValue({
      stations: [
        {
          station_id: "S001",
          name: "TP.HCM East Gateway",
          lat: 10.7769,
          lng: 106.7009,
          n_ports: 4,
          power_kw: 120,
          connector_types: ["CCS2"],
          network: "phase0-demo",
          station_type: "urban",
          source: "phase0-fixture",
          assumptions: [],
        },
      ],
      data_type: "mock",
      source_notes: [],
    }),
    getRoutes: vi.fn().mockResolvedValue([]),
    recommend: vi.fn(),
    predict: vi.fn(),
    getPressure: vi.fn(),
    pressure: vi.fn(),
    simulate: vi.fn(),
    reset: vi.fn(),
    whatif: vi.fn(),
    ...overrides,
  } as unknown as ApiClient;
}

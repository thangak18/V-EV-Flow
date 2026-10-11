import { vi } from "vitest";

import { ApiClient } from "../services/api";

export function createMockApiClient(
  overrides: Partial<ApiClient> = {},
): ApiClient {
  return {
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
    recommend: vi.fn(),
    predict: vi.fn(),
    getPressure: vi.fn(),
    pressure: vi.fn(),
    simulate: vi.fn(),
    reset: vi.fn(),
    ...overrides,
  } as unknown as ApiClient;
}

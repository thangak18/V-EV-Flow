import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { ApiError } from "../services/api";
import { createMockApiClient } from "../test/mockApiClient";
import { useRecommendation } from "./useRecommendation";

const request = {
  request_id: "r1",
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

describe("useRecommendation", () => {
  test("marks empty when primary and backup are null", async () => {
    const recommend = vi.fn().mockResolvedValue({
      request_id: "r1",
      primary: null,
      backup: null,
      reasons: ["none"],
      model_version: "v1",
      allocation_method: "ranking_penalty",
      data_type: "mock",
      contract_version: "0.1.0",
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <ApiProvider client={createMockApiClient({ recommend })}>
        {children}
      </ApiProvider>
    );

    const { result } = renderHook(() => useRecommendation(), { wrapper });
    await act(async () => {
      await result.current.submit(request);
    });
    await waitFor(() => expect(result.current.status).toBe("empty"));
  });

  test("surfaces API errors and retries the last payload", async () => {
    const recommend = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(500, "boom", "boom", null))
      .mockResolvedValueOnce({
        request_id: "r1",
        primary: {
          station_id: "S001",
          eta: "2026-10-13T16:40:00+07:00",
          distance_km: 10,
          detour_km: 1,
          arrival_soc_pct: 18,
          p_available: 0.7,
        },
        backup: null,
        reasons: ["ok"],
        model_version: "v1",
        allocation_method: "ranking_penalty",
        data_type: "mock",
        contract_version: "0.1.0",
      });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <ApiProvider client={createMockApiClient({ recommend })}>
        {children}
      </ApiProvider>
    );

    const { result } = renderHook(() => useRecommendation(), { wrapper });
    await act(async () => {
      await result.current.submit(request);
    });
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toBe("boom");

    await act(async () => {
      result.current.retry();
    });
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(recommend).toHaveBeenCalledTimes(2);
  });
});

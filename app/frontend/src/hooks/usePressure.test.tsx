import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { ApiError } from "../services/api";
import { createMockApiClient } from "../test/mockApiClient";
import { usePressure } from "./usePressure";

describe("usePressure", () => {
  test("loads success empty and error states", async () => {
    const getPressure = vi
      .fn()
      .mockResolvedValueOnce({
        time: "t",
        scenario: "normal",
        contract_version: "0.1.0",
        stations: [
          {
            station_id: "S001",
            p_available: 0.5,
            pressure_score: 0.5,
            data_type: "mock",
          },
        ],
      })
      .mockResolvedValueOnce({
        time: "t",
        scenario: "normal",
        contract_version: "0.1.0",
        stations: [],
      })
      .mockRejectedValueOnce(
        new ApiError(503, "pressure_down", "pressure down", null),
      );

    const wrapper = ({ children }: { children: ReactNode }) => (
      <ApiProvider client={createMockApiClient({ getPressure })}>
        {children}
      </ApiProvider>
    );

    const { result } = renderHook(() => usePressure(), { wrapper });

    await act(async () => {
      await result.current.load("normal", "2026-10-13T16:00:00+07:00");
    });
    await waitFor(() => expect(result.current.status).toBe("success"));

    await act(async () => {
      await result.current.load("tet", "2026-10-13T16:00:00+07:00");
    });
    await waitFor(() => expect(result.current.status).toBe("empty"));

    await act(async () => {
      await result.current.load("holiday_30_4", "2026-10-13T16:00:00+07:00");
    });
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toBe("pressure down");
  });
});

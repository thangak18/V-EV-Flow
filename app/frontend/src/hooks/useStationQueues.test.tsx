import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { ApiError } from "../services/api";
import { createMockApiClient } from "../test/mockApiClient";
import { useStationQueues } from "./useStationQueues";

const view = {
  station_id: "S001",
  observed_at: "2026-10-17T18:00:00+07:00",
  vehicles_waiting: 3,
  vehicles_charging: 1,
  confidence: 0.8,
  source: "camera_mock",
  data_type: "mock",
};

function wrapperFor(getStationQueues: ReturnType<typeof vi.fn>) {
  return ({ children }: { children: ReactNode }) => (
    <ApiProvider client={createMockApiClient({ getStationQueues })}>
      {children}
    </ApiProvider>
  );
}

describe("useStationQueues", () => {
  test("indexes camera views by station for the chosen time and scenario", async () => {
    const getStationQueues = vi.fn().mockResolvedValue({
      observed_at: view.observed_at,
      scenario: "tet",
      observations: [view],
      data_type: "mock",
      source_notes: [],
    });
    const { result } = renderHook(
      () => useStationQueues("tet", "2026-10-17T18:00:00+07:00"),
      { wrapper: wrapperFor(getStationQueues) },
    );
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.byStation.get("S001")?.vehicles_waiting).toBe(3);
    expect(result.current.byStation.get("S999")).toBeUndefined();
    expect(getStationQueues.mock.calls[0][0]).toEqual({
      observed_at: "2026-10-17T18:00:00+07:00",
      scenario: "tet",
    });
  });

  test("a failed camera feed is not fatal and shows no cameras", async () => {
    const getStationQueues = vi
      .fn()
      .mockRejectedValue(new ApiError(503, "down", "camera down", null));
    const { result } = renderHook(() => useStationQueues("normal", undefined), {
      wrapper: wrapperFor(getStationQueues),
    });
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.byStation.size).toBe(0);
  });

  test("refetches when the scenario changes and drops the old views", async () => {
    const getStationQueues = vi
      .fn()
      .mockResolvedValueOnce({
        observed_at: view.observed_at,
        scenario: "normal",
        observations: [view],
        data_type: "mock",
        source_notes: [],
      })
      .mockResolvedValueOnce({
        observed_at: view.observed_at,
        scenario: "tet",
        observations: [],
        data_type: "mock",
        source_notes: [],
      });
    const { result, rerender } = renderHook(
      ({ scenario }) => useStationQueues(scenario, view.observed_at),
      {
        wrapper: wrapperFor(getStationQueues),
        initialProps: { scenario: "normal" as "normal" | "tet" },
      },
    );
    await waitFor(() => expect(result.current.byStation.size).toBe(1));
    rerender({ scenario: "tet" });
    await waitFor(() => expect(result.current.byStation.size).toBe(0));
    expect(getStationQueues).toHaveBeenCalledTimes(2);
  });
});

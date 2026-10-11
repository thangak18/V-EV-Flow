import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { createMockApiClient } from "../test/mockApiClient";
import { useSimulationComparison } from "./useSimulationComparison";

describe("useSimulationComparison", () => {
  test("runs three strategies and keeps partial failures", async () => {
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string }) => {
        if (body.strategy === "currently_available") {
          throw new Error("sim failed");
        }
        return {
          scenario: "normal",
          seed: 42,
          strategy: body.strategy,
          model_version: "fake-sim-v1",
          fixture_hash: "hashhashhash",
          contract_version: "0.1.0",
          metrics: {
            success_rate: 0.9,
            mean_detour_km: 2,
            mean_wait_minutes: 3,
            failed_count: 10,
            vehicle_count: 100,
          },
        };
      });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <ApiProvider client={createMockApiClient({ simulate })}>
        {children}
      </ApiProvider>
    );

    const { result } = renderHook(() => useSimulationComparison(), { wrapper });
    await act(async () => {
      await result.current.run("normal", 42, 100);
    });
    await waitFor(() => expect(result.current.rows).toHaveLength(3));
    expect(simulate).toHaveBeenCalledTimes(3);
    expect(
      result.current.rows.filter((row) => row.status === "error"),
    ).toHaveLength(1);
  });
});

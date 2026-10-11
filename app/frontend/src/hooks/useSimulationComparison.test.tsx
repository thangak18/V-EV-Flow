import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { createMockApiClient } from "../test/mockApiClient";
import { useSimulationComparison } from "./useSimulationComparison";

const FIXTURE_HASH =
  "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const OTHER_HASH =
  "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";

function okResult(strategy: string, overrides: Record<string, unknown> = {}) {
  return {
    scenario: "normal",
    seed: 42,
    strategy,
    model_version: "fake-sim-v1",
    fixture_hash: FIXTURE_HASH,
    contract_version: "0.1.0",
    metrics: {
      success_rate: 0.9,
      mean_detour_km: 2,
      mean_wait_minutes: 3,
      failed_count: 10,
      vehicle_count: 100,
    },
    ...overrides,
  };
}

describe("useSimulationComparison", () => {
  test("runs three strategies and keeps partial failures", async () => {
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string }) => {
        if (body.strategy === "currently_available") {
          throw new Error("sim failed");
        }
        return okResult(body.strategy);
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

  test("rejects responses that mislabel strategy", async () => {
    // Backend always returns strategy=nearest regardless of request.
    const simulate = vi.fn().mockResolvedValue(okResult("nearest"));
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
    expect(result.current.rows[0]).toMatchObject({
      strategy: "nearest",
      status: "success",
    });
    expect(result.current.rows[1]).toMatchObject({
      strategy: "currently_available",
      status: "error",
    });
    expect(result.current.rows[2]).toMatchObject({
      strategy: "ai_allocation",
      status: "error",
    });
    expect(
      result.current.rows
        .filter((row) => row.status === "error")
        .every((row) => /does not match requested/i.test(row.message)),
    ).toBe(true);
  });

  test("rejects mismatched fixture hashes across the comparison set", async () => {
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string }) =>
        okResult(body.strategy, {
          fixture_hash:
            body.strategy === "ai_allocation" ? OTHER_HASH : FIXTURE_HASH,
        }),
      );
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
    expect(
      result.current.rows.every(
        (row) =>
          row.status === "error" && /fixture_hash mismatch/i.test(row.message),
      ),
    ).toBe(true);
  });

  test("rejects seed or vehicle_count drift from the request", async () => {
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string }) =>
        okResult(body.strategy, {
          seed: 99,
          metrics: {
            success_rate: 0.9,
            mean_detour_km: 2,
            mean_wait_minutes: 3,
            failed_count: 10,
            vehicle_count: 50,
          },
        }),
      );
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
    expect(result.current.rows.every((row) => row.status === "error")).toBe(
      true,
    );
  });
});

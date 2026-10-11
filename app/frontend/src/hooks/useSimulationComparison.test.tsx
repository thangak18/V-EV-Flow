import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { FIXTURE_HASH, OTHER_FIXTURE_HASH } from "../test/fixtureHash";
import { createMockApiClient } from "../test/mockApiClient";
import { useSimulationComparison } from "./useSimulationComparison";

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
    expect(result.current.rows[1]?.status).toBe("error");
    expect(result.current.rows[2]?.status).toBe("error");
  });

  test("rejects mismatched fixture hashes across the comparison set", async () => {
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string }) =>
        okResult(body.strategy, {
          fixture_hash:
            body.strategy === "ai_allocation"
              ? OTHER_FIXTURE_HASH
              : FIXTURE_HASH,
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

  test("clears previous rows as soon as a new run starts", async () => {
    const gate = {
      release: null as null | (() => void),
      wait: Promise.resolve(),
    };
    gate.wait = new Promise<void>((resolve) => {
      gate.release = resolve;
    });

    let phase: "first" | "second" = "first";
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string; seed: number }) => {
        if (phase === "second") {
          await gate.wait;
        }
        return okResult(body.strategy, { seed: body.seed });
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
    expect(result.current.config?.seed).toBe(42);

    phase = "second";
    let secondRun!: Promise<void>;
    await act(async () => {
      secondRun = result.current.run("normal", 99, 100);
    });

    await waitFor(() => {
      expect(result.current.pending).toBe(true);
      expect(result.current.config?.seed).toBe(99);
      expect(result.current.rows).toHaveLength(0);
    });

    await act(async () => {
      gate.release?.();
      await secondRun;
    });
    await waitFor(() => {
      expect(result.current.pending).toBe(false);
      expect(result.current.rows).toHaveLength(3);
      expect(result.current.config?.seed).toBe(99);
    });
  });
});

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

test("late responses cannot overwrite a newer scenario request", async () => {
  type Response = import("../services/api").PressureResponse;
  let finishFirst!: (response: Response) => void;
  const latest: Response = {
    time: "2026-10-13T16:00:00+07:00",
    scenario: "tet",
    contract_version: "0.1.0",
    stations: [],
  };
  const getPressure = vi
    .fn()
    .mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          finishFirst = resolve;
        }),
    )
    .mockResolvedValueOnce(latest);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <ApiProvider client={createMockApiClient({ getPressure })}>
      {children}
    </ApiProvider>
  );
  const { result } = renderHook(() => usePressure(), { wrapper });
  let oldRequest!: Promise<void>;
  act(() => {
    oldRequest = result.current.load("normal", latest.time);
  });
  await act(async () => {
    await result.current.load("tet", latest.time);
  });
  await act(async () => {
    finishFirst({ ...latest, scenario: "normal" });
    await oldRequest;
  });
  expect(result.current.result?.scenario).toBe("tet");
  expect(result.current.resultKey).toBe(`tet|${latest.time}`);
  expect(getPressure.mock.calls[0]?.[1].aborted).toBe(true);
});

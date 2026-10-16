import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import { ApiProvider } from "../app/ApiContext";
import { createMockApiClient } from "../test/mockApiClient";
import { useDriverRoutes } from "./useDriverRoutes";

const leg = {
  id: "primary",
  label: "Main",
  color: "green",
  origin: { lat: 10.7, lng: 106.7 },
  destination: { lat: 11, lng: 107 },
  depart_time: "2026-10-13T16:00:00+07:00",
};
const road = {
  source: "goong-directions-v2",
  distance_km: 10,
  duration_minutes: 15,
  geometry: [leg.origin, { lat: 10.9, lng: 106.9 }, leg.destination],
};

test("road overlays use provider geometry and never allocate again", async () => {
  const getRoutes = vi.fn().mockResolvedValue([road]);
  const client = createMockApiClient({ getRoutes });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <ApiProvider client={client}>{children}</ApiProvider>
  );
  const { result, rerender } = renderHook(({ legs }) => useDriverRoutes(legs), {
    wrapper,
    initialProps: { legs: [leg] },
  });
  await waitFor(() => expect(result.current.routes).toHaveLength(1));
  expect(result.current.routes[0]?.coordinates).toEqual(road.geometry);
  rerender({ legs: [{ ...leg }] });
  expect(getRoutes).toHaveBeenCalledTimes(1);
  expect(client.recommend).not.toHaveBeenCalled();
  getRoutes.mockResolvedValueOnce([
    { ...road, source: "fake", geometry: null },
  ]);
  rerender({ legs: [{ ...leg, id: "backup" }] });
  await waitFor(() => expect(result.current.missing).toBe(true));
  expect(result.current.routes).toEqual([]);
});

test("late route responses cannot restore an edited trip", async () => {
  let finish!: (value: (typeof road)[]) => void;
  const getRoutes = vi.fn().mockImplementation(
    () =>
      new Promise<(typeof road)[]>((resolve) => {
        finish = resolve;
      }),
  );
  const wrapper = ({ children }: { children: ReactNode }) => (
    <ApiProvider client={createMockApiClient({ getRoutes })}>
      {children}
    </ApiProvider>
  );
  const { result, rerender } = renderHook(({ legs }) => useDriverRoutes(legs), {
    wrapper,
    initialProps: { legs: [leg] },
  });
  rerender({ legs: [] });
  await act(async () => {
    finish([road]);
  });
  expect(result.current.routes).toEqual([]);
  expect(getRoutes.mock.calls[0]?.[1].aborted).toBe(true);
});

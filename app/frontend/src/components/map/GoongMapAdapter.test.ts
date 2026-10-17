import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { GoongMapAdapter } from "./GoongMapAdapter";
import type { MapModel } from "./types";

const model: MapModel = {
  points: [
    {
      id: "origin",
      lat: 10.78,
      lng: 106.7,
      label: "Origin",
      role: "origin",
    },
  ],
};

type MockMap = {
  remove: ReturnType<typeof vi.fn>;
  on: ReturnType<typeof vi.fn>;
  flyTo: ReturnType<typeof vi.fn>;
  addControl: ReturnType<typeof vi.fn>;
};

function installGoongMocks(options?: {
  emitLoad?: boolean;
  delayMs?: number;
  styleReady?: boolean;
}): {
  Map: ReturnType<typeof vi.fn>;
  maps: MockMap[];
  markerElements: HTMLElement[];
} {
  const maps: MockMap[] = [];
  const Map = vi.fn(function MockMap(this: MockMap) {
    const map: MockMap = {
      remove: vi.fn(),
      on: vi.fn((event: string, cb: () => void) => {
        if (
          (event === "style.load" && options?.styleReady) ||
          (event === "load" && options?.emitLoad !== false)
        ) {
          queueMicrotask(cb);
        }
      }),
      flyTo: vi.fn(),
      addControl: vi.fn(),
    };
    maps.push(map);
    Object.assign(this, map);
    return map;
  });

  const markerElements: HTMLElement[] = [];
  const Marker = vi.fn(function MockMarker(this: {
    setLngLat: ReturnType<typeof vi.fn>;
    addTo: ReturnType<typeof vi.fn>;
    remove: ReturnType<typeof vi.fn>;
    getElement: ReturnType<typeof vi.fn>;
  }) {
    this.setLngLat = vi.fn().mockReturnValue(this);
    this.addTo = vi.fn().mockReturnValue(this);
    this.remove = vi.fn();
    this.getElement = vi.fn(() => {
      const el = document.createElement("div");
      markerElements.push(el);
      return el;
    });
    return this;
  });

  const attach = () => {
    window.goongjs = {
      accessToken: "",
      Map: Map as unknown as NonNullable<typeof window.goongjs>["Map"],
      Marker: Marker as unknown as NonNullable<typeof window.goongjs>["Marker"],
      NavigationControl: vi.fn() as unknown as NonNullable<
        typeof window.goongjs
      >["NavigationControl"],
    };
  };

  if ((options?.delayMs ?? 0) <= 0) {
    attach();
  } else {
    window.setTimeout(attach, options?.delayMs);
  }

  return { Map, maps, markerElements };
}

describe("GoongMapAdapter", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_GOONG_MAP_KEY", "test-maptiles-key");
    vi.useFakeTimers();
    delete window.goongjs;
    document.head
      .querySelectorAll('script[src*="goong-js"], link[href*="goong-js"]')
      .forEach((node) => node.remove());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
    delete window.goongjs;
  });

  test("zooms to the requested primary or backup instead of the trip origin", async () => {
    const { maps } = installGoongMocks();
    const adapter = new GoongMapAdapter();
    const primary = {
      id: "A",
      role: "primary" as const,
      label: "Primary",
      lat: 10.8,
      lng: 106.8,
    };
    const backup = {
      id: "B",
      role: "backup" as const,
      label: "Backup",
      lat: 11,
      lng: 107,
    };
    const points = [...model.points, primary, backup];
    const mounting = adapter.mount(document.createElement("div"), { points });
    await vi.advanceTimersByTimeAsync(0);
    await mounting;
    await adapter.update({
      points,
      focus: { id: "A", role: "primary", sequence: 1 },
    });
    expect(maps[0]!.flyTo).toHaveBeenLastCalledWith({
      center: [106.8, 10.8],
      zoom: 14,
    });
    await adapter.update({
      points,
      focus: { id: "B", role: "backup", sequence: 2 },
    });
    expect(maps[0]!.flyTo).toHaveBeenLastCalledWith({
      center: [107, 11],
      zoom: 14,
    });
    await adapter.update({
      points,
      focus: { id: "B", role: "backup", sequence: 3 },
    });
    expect(maps[0]!.flyTo).toHaveBeenCalledTimes(3);
    adapter.destroy();
  });

  test("does not construct a map after destroy during SDK load", async () => {
    const { Map } = installGoongMocks({ delayMs: 100 });
    const container = document.createElement("div");
    const adapter = new GoongMapAdapter();

    const mountPromise = adapter.mount(container, model);
    // Flush script insertion; SDK attach is still delayed.
    await Promise.resolve();
    const script = document.querySelector<HTMLScriptElement>(
      'script[src*="goong-js"]',
    );
    expect(script).toBeTruthy();

    adapter.destroy();
    await vi.advanceTimersByTimeAsync(100);
    script?.onload?.(new Event("load"));
    await expect(mountPromise).resolves.toBeUndefined();
    expect(Map).not.toHaveBeenCalled();
  });

  test("times out when the Goong SDK never becomes available", async () => {
    const container = document.createElement("div");
    const adapter = new GoongMapAdapter();

    const mountPromise = adapter.mount(container, model);
    await Promise.resolve();
    const rejection = expect(mountPromise).rejects.toThrow(
      /Timed out loading Goong JS SDK/i,
    );
    await vi.advanceTimersByTimeAsync(15_000);
    await rejection;
  });

  test("times out when map load never fires and tears down the instance", async () => {
    const { maps } = installGoongMocks({ emitLoad: false });
    const container = document.createElement("div");
    const adapter = new GoongMapAdapter();

    const mountPromise = adapter.mount(container, model);
    const rejection = expect(mountPromise).rejects.toThrow(
      /Timed out waiting for Goong map load/i,
    );
    await vi.advanceTimersByTimeAsync(15_000);
    await rejection;
    expect(maps[0]?.remove).toHaveBeenCalled();
  });
});

test("style readiness renders overlays even when full tile load is delayed", async () => {
  vi.stubEnv("VITE_GOONG_MAP_KEY", "test-maptiles-key");
  const { maps } = installGoongMocks({ emitLoad: false, styleReady: true });
  const adapter = new GoongMapAdapter();
  await adapter.mount(document.createElement("div"), model);
  const map = maps[0]!;
  const addSource = vi.fn(),
    addLayer = vi.fn(),
    fitBounds = vi.fn();
  Object.assign(map, { addSource, addLayer, fitBounds });
  await adapter.update({
    ...model,
    fitBounds: true,
    points: [
      ...model.points,
      { ...model.points[0]!, id: "end", lat: 11, lng: 107 },
    ],
    routes: [
      {
        id: "road",
        label: "Road",
        color: "green",
        coordinates: [
          { lat: 10.78, lng: 106.7 },
          { lat: 10.9, lng: 106.8 },
          { lat: 11, lng: 107 },
        ],
      },
    ],
  });
  expect(addSource).toHaveBeenCalledWith(
    "charging-route-road",
    expect.objectContaining({
      data: expect.objectContaining({
        geometry: {
          type: "LineString",
          coordinates: [
            [106.7, 10.78],
            [106.8, 10.9],
            [107, 11],
          ],
        },
      }),
    }),
  );
  expect(addLayer).toHaveBeenCalled();
  expect(fitBounds).toHaveBeenCalledWith(
    [
      [106.7, 10.78],
      [107, 11],
    ],
    expect.any(Object),
  );
  adapter.destroy();
  vi.unstubAllEnvs();
  delete window.goongjs;
});

test("marks a camera station with an icon and its summary", async () => {
  vi.stubEnv("VITE_GOONG_MAP_KEY", "test-maptiles-key");
  const { markerElements } = installGoongMocks();
  const adapter = new GoongMapAdapter();
  await adapter.mount(document.createElement("div"), {
    points: [
      {
        id: "S1",
        lat: 10.7,
        lng: 106.7,
        label: "Trạm A",
        role: "primary",
        camera: "5 xe chờ",
      },
      { id: "S2", lat: 10.8, lng: 106.8, label: "Trạm B", role: "backup" },
    ],
  });
  const [withCamera, without] = markerElements;
  expect(withCamera.title).toContain("5 xe chờ");
  expect(withCamera.querySelector(".map-marker-label")?.textContent).toContain(
    "📹",
  );
  expect(without.title).not.toContain("xe chờ");
  expect(without.querySelector(".map-marker-label")).toBeNull();
  adapter.destroy();
  vi.unstubAllEnvs();
  delete window.goongjs;
});

test("shows the waiting-vehicle count on station markers instead of 1/2", async () => {
  vi.stubEnv("VITE_GOONG_MAP_KEY", "test-maptiles-key");
  const { markerElements } = installGoongMocks();
  const adapter = new GoongMapAdapter();
  await adapter.mount(document.createElement("div"), {
    points: [
      {
        id: "S1",
        lat: 10.7,
        lng: 106.7,
        label: "Trạm A",
        role: "primary",
        queue: 3,
      },
      { id: "S2", lat: 10.8, lng: 106.8, label: "Trạm B", role: "backup" },
    ],
  });
  const [primary, backup] = markerElements;
  expect(primary.querySelector(".map-marker-queue")?.textContent).toBe(
    "3 xe chờ",
  );
  expect(primary.querySelector(".map-marker-label")?.textContent).not.toMatch(
    /^1/,
  );
  expect(backup.querySelector(".map-marker-queue")).toBeNull();
  adapter.destroy();
  vi.unstubAllEnvs();
  delete window.goongjs;
});

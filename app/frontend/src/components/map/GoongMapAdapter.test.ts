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
}): {
  Map: ReturnType<typeof vi.fn>;
  maps: MockMap[];
} {
  const maps: MockMap[] = [];
  const Map = vi.fn(function MockMap(this: MockMap) {
    const map: MockMap = {
      remove: vi.fn(),
      on: vi.fn((event: string, cb: () => void) => {
        if (event === "load" && options?.emitLoad !== false) {
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

  return { Map, maps };
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

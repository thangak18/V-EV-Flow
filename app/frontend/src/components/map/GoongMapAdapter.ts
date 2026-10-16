import type { MapAdapter, MapModel, MapPoint } from "./types";

const GOONG_JS =
  "https://cdn.jsdelivr.net/npm/@goongmaps/goong-js@1.0.9/dist/goong-js.js";
const GOONG_CSS =
  "https://cdn.jsdelivr.net/npm/@goongmaps/goong-js@1.0.9/dist/goong-js.css";
const GOONG_STYLE = "https://tiles.goong.io/assets/goong_map_web.json";
const LOAD_TIMEOUT_MS = 15_000;

type GoongMap = {
  remove: () => void;
  on: (event: string, cb: () => void) => void;
  flyTo: (opts: { center: [number, number]; zoom?: number }) => void;
  addControl: (control: unknown) => void;
};

type GoongMarker = {
  setLngLat: (lngLat: [number, number]) => GoongMarker;
  addTo: (map: GoongMap) => GoongMarker;
  remove: () => void;
  getElement: () => HTMLElement;
};

type GoongNamespace = {
  accessToken: string;
  Map: new (options: {
    container: HTMLElement;
    style: string;
    center: [number, number];
    zoom: number;
  }) => GoongMap;
  Marker: new (options?: { color?: string }) => GoongMarker;
  NavigationControl: new () => unknown;
};

declare global {
  interface Window {
    goongjs?: GoongNamespace;
  }
}

function toLngLat(point: MapPoint): [number, number] {
  return [point.lng, point.lat];
}

async function ensureGoong(
  timeoutMs = LOAD_TIMEOUT_MS,
): Promise<GoongNamespace> {
  if (window.goongjs) return window.goongjs;

  if (!document.querySelector(`link[href="${GOONG_CSS}"]`)) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = GOONG_CSS;
    document.head.appendChild(link);
  }

  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GOONG_JS}"]`,
    );
    if (existing && window.goongjs) {
      resolve();
      return;
    }

    const script = existing ?? document.createElement("script");
    let settled = false;
    const timer = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error("Timed out loading Goong JS SDK"));
    }, timeoutMs);

    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      if (error) reject(error);
      else resolve();
    };

    script.async = true;
    script.onload = () => finish();
    script.onerror = () => finish(new Error("Failed to load Goong JS SDK"));
    if (!existing) {
      script.src = GOONG_JS;
      document.head.appendChild(script);
    } else if (!window.goongjs) {
      // Script tag exists but SDK never attached — wait with timeout.
      const poll = window.setInterval(() => {
        if (window.goongjs) {
          window.clearInterval(poll);
          finish();
        }
      }, 50);
      window.setTimeout(() => {
        window.clearInterval(poll);
        finish(new Error("Goong JS SDK script present but unavailable"));
      }, timeoutMs);
    }
  });

  if (!window.goongjs) {
    throw new Error("Goong JS SDK unavailable after script load");
  }
  return window.goongjs;
}

function waitForMapLoad(
  map: GoongMap,
  timeoutMs = LOAD_TIMEOUT_MS,
): Promise<void> {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error("Timed out waiting for Goong map load"));
    }, timeoutMs);
    map.on("load", () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      resolve();
    });
  });
}

export class GoongMapAdapter implements MapAdapter {
  private map: GoongMap | null = null;
  private markers: GoongMarker[] = [];
  private generation = 0;
  private destroyed = false;

  async mount(container: HTMLElement, model: MapModel): Promise<void> {
    const mountGeneration = ++this.generation;
    this.destroyed = false;

    const key = import.meta.env.VITE_GOONG_MAP_KEY as string | undefined;
    if (!key?.trim()) {
      throw new Error("VITE_GOONG_MAP_KEY is missing for real-map mode");
    }

    const goongjs = await ensureGoong();
    if (this.isStale(mountGeneration)) return;

    goongjs.accessToken = key;
    const center = model.points[0]
      ? toLngLat(model.points[0])
      : ([106.7, 10.78] as [number, number]);

    this.map = new goongjs.Map({
      container,
      style: GOONG_STYLE,
      center,
      zoom: 8,
    });
    this.map.addControl(new goongjs.NavigationControl());

    try {
      await waitForMapLoad(this.map);
    } catch (error) {
      this.teardownMap();
      throw error;
    }

    if (this.isStale(mountGeneration)) {
      this.teardownMap();
      return;
    }

    this.renderMarkers(goongjs, model);
  }

  async update(model: MapModel): Promise<void> {
    if (!this.map || !window.goongjs || this.destroyed) return;
    this.clearMarkers();
    this.renderMarkers(window.goongjs, model);
    const focused =
      model.focus &&
      model.points.find(
        (point) =>
          point.id === model.focus!.id && point.role === model.focus!.role,
      );
    const target = focused || model.points[0];
    if (target)
      this.map.flyTo({ center: toLngLat(target), zoom: focused ? 14 : 8 });
  }

  destroy(): void {
    this.destroyed = true;
    this.generation += 1;
    this.teardownMap();
  }

  private isStale(mountGeneration: number): boolean {
    return this.destroyed || mountGeneration !== this.generation;
  }

  private teardownMap(): void {
    this.clearMarkers();
    this.map?.remove();
    this.map = null;
  }

  private renderMarkers(goongjs: GoongNamespace, model: MapModel): void {
    if (!this.map) return;
    for (const point of model.points) {
      const color =
        point.color ??
        (point.role === "primary"
          ? "#146c52"
          : point.role === "backup"
            ? "#b45309"
            : "#334155");
      const marker = new goongjs.Marker({ color })
        .setLngLat(toLngLat(point))
        .addTo(this.map);
      const element = marker.getElement();
      element.title = `${point.role}: ${point.label}`;
      if (model.focus?.id === point.id && model.focus.role === point.role) {
        element.classList.add("map-marker--focused");
        element.setAttribute("aria-current", "location");
      }
      this.markers.push(marker);
    }
  }

  private clearMarkers(): void {
    for (const marker of this.markers) marker.remove();
    this.markers = [];
  }
}

export const GOONG_SDK_RECORD = {
  name: "@goongmaps/goong-js",
  version: "1.0.9",
  delivery: "jsDelivr CDN script + CSS (official Goong docs)",
  style: GOONG_STYLE,
  coordinateOrder: "[lng, lat] inside GoongMapAdapter only",
  keyEnv: "VITE_GOONG_MAP_KEY",
  attribution: "Map tiles © Goong",
} as const;

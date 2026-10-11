import type { MapAdapter, MapModel, MapPoint } from "./types";

const GOONG_JS =
  "https://cdn.jsdelivr.net/npm/@goongmaps/goong-js@1.0.9/dist/goong-js.js";
const GOONG_CSS =
  "https://cdn.jsdelivr.net/npm/@goongmaps/goong-js@1.0.9/dist/goong-js.css";
const GOONG_STYLE = "https://tiles.goong.io/assets/goong_map_web.json";

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

async function ensureGoong(): Promise<GoongNamespace> {
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
    script.src = GOONG_JS;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Goong JS SDK"));
    if (!existing) document.head.appendChild(script);
  });

  if (!window.goongjs) {
    throw new Error("Goong JS SDK unavailable after script load");
  }
  return window.goongjs;
}

export class GoongMapAdapter implements MapAdapter {
  private map: GoongMap | null = null;
  private markers: GoongMarker[] = [];

  async mount(container: HTMLElement, model: MapModel): Promise<void> {
    const key = import.meta.env.VITE_GOONG_MAP_KEY as string | undefined;
    if (!key) {
      throw new Error("VITE_GOONG_MAP_KEY is missing for real-map mode");
    }

    const goongjs = await ensureGoong();
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

    await new Promise<void>((resolve) => {
      this.map?.on("load", () => resolve());
    });
    this.renderMarkers(goongjs, model);
  }

  async update(model: MapModel): Promise<void> {
    if (!this.map || !window.goongjs) return;
    this.clearMarkers();
    this.renderMarkers(window.goongjs, model);
    if (model.points[0]) {
      this.map.flyTo({ center: toLngLat(model.points[0]), zoom: 8 });
    }
  }

  destroy(): void {
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
      marker.getElement().title = `${point.role}: ${point.label}`;
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

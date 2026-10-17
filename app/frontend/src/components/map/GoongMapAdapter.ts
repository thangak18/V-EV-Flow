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
  fitBounds?: (
    bounds: [[number, number], [number, number]],
    options: object,
  ) => void;
  resize?: () => void;
  getSource?: (id: string) => { setData: (data: object) => void } | undefined;
  addSource?: (id: string, source: object) => void;
  addLayer?: (layer: object) => void;
  getLayer?: (id: string) => unknown;
  removeLayer?: (id: string) => void;
  removeSource?: (id: string) => void;
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

let sdkLoading: Promise<void> | null = null;
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
  if (!sdkLoading) {
    sdkLoading = new Promise<void>((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>(
        `script[src="${GOONG_JS}"]`,
      );
      const script = existing ?? document.createElement("script");
      const finish = (error?: Error) => {
        window.clearTimeout(timer);
        script.onload = null;
        script.onerror = null;
        if (error) {
          script.remove();
          reject(error);
        } else resolve();
      };
      const timer = window.setTimeout(
        () => finish(new Error("Timed out loading Goong JS SDK")),
        timeoutMs,
      );
      script.async = true;
      script.onload = () =>
        finish(
          window.goongjs
            ? undefined
            : new Error("Goong JS SDK unavailable after script load"),
        );
      script.onerror = () => finish(new Error("Failed to load Goong JS SDK"));
      if (!existing) {
        script.src = GOONG_JS;
        document.head.appendChild(script);
      }
    }).finally(() => {
      sdkLoading = null;
    });
  }
  await sdkLoading;
  if (!window.goongjs)
    throw new Error("Goong JS SDK unavailable after script load");
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
    const ready = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      resolve();
    };
    // style.load permits overlays without waiting for every tile/font request.
    map.on("style.load", ready);
    map.on("load", ready);
  });
}

export class GoongMapAdapter implements MapAdapter {
  private map: GoongMap | null = null;
  private markers: GoongMarker[] = [];
  private generation = 0;
  private destroyed = false;
  private routeIds: string[] = [];
  private resizeObserver: ResizeObserver | null = null;

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

    container.dataset.mapAdapter = "goong";
    this.map = new goongjs.Map({
      container,
      style: GOONG_STYLE,
      center,
      zoom: 8,
    });
    this.map.addControl(new goongjs.NavigationControl());
    if (typeof ResizeObserver !== "undefined") {
      this.resizeObserver = new ResizeObserver(() => this.map?.resize?.());
      this.resizeObserver.observe(container);
    }

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
    this.renderRoutes(model);
  }

  async update(model: MapModel): Promise<void> {
    if (!this.map || !window.goongjs || this.destroyed) return;
    this.clearMarkers();
    this.renderMarkers(window.goongjs, model);
    this.renderRoutes(model);
    this.positionCamera(model);
  }

  private positionCamera(model: MapModel): void {
    if (!this.map) return;
    const focused =
      model.focus &&
      model.points.find(
        (point) =>
          point.id === model.focus!.id && point.role === model.focus!.role,
      );
    if (focused) {
      this.map.flyTo({ center: toLngLat(focused), zoom: 14 });
      return;
    }
    if (model.fitBounds && model.points.length > 1 && this.map.fitBounds) {
      const coordinates = [
        ...model.points,
        ...(model.routes ?? []).flatMap((route) => route.coordinates),
      ];
      const lngs = coordinates.map((point) => point.lng),
        lats = coordinates.map((point) => point.lat);
      this.map.fitBounds(
        [
          [Math.min(...lngs), Math.min(...lats)],
          [Math.max(...lngs), Math.max(...lats)],
        ],
        {
          padding: 64,
          maxZoom: 13,
          duration: window.matchMedia?.("(prefers-reduced-motion: reduce)")
            .matches
            ? 0
            : 600,
        },
      );
    } else if (model.points[0])
      this.map.flyTo({ center: toLngLat(model.points[0]), zoom: 8 });
  }

  private renderRoutes(model: MapModel): void {
    const map = this.map;
    if (!map?.addSource || !map.addLayer) return;
    for (const id of this.routeIds) {
      if (map.getLayer?.(id)) map.removeLayer?.(id);
      if (map.getSource?.(id)) map.removeSource?.(id);
    }
    this.routeIds = [];
    for (const route of model.routes ?? []) {
      if (route.coordinates.length < 2) continue;
      const id = `charging-route-${route.id}`;
      map.addSource(id, {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: route.coordinates.map((point) => [
              point.lng,
              point.lat,
            ]),
          },
        },
      });
      map.addLayer({
        id,
        type: "line",
        source: id,
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": route.color,
          "line-width": route.dashed ? 5 : 6,
          "line-opacity": 0.9,
          ...(route.dashed ? { "line-dasharray": [2, 2] } : {}),
        },
      });
      this.routeIds.push(id);
    }
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
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.routeIds = [];
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
      const roles = {
        origin: "Điểm đi",
        destination: "Điểm đến",
        primary: "Trạm chính",
        backup: "Trạm dự phòng",
        pressure: "Trạm sạc",
      };
      element.dataset.mapRole = point.role;
      element.title = point.camera
        ? `${roles[point.role]}: ${point.label} — ${point.camera}`
        : `${roles[point.role]}: ${point.label}`;
      element.setAttribute("aria-label", element.title);
      const badge =
        point.badge ??
        {
          origin: "A",
          destination: "B",
          primary: "1",
          backup: "2",
          pressure: "",
        }[point.role];
      if (badge || point.camera) {
        const tag = document.createElement("span");
        tag.className = "map-marker-label";
        const text = badge
          ? `${badge} · ${roles[point.role]}: ${point.label}`
          : `${roles[point.role]}: ${point.label}`;
        tag.textContent = point.camera ? `📹 ${text}` : text;
        element.appendChild(tag);
      }
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

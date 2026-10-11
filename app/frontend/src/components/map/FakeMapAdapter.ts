import type { MapAdapter, MapModel, MapPoint } from "./types";

const ROLE_COLOR: Record<MapPoint["role"], string> = {
  origin: "#0f766e",
  destination: "#1d4ed8",
  primary: "#146c52",
  backup: "#b45309",
  pressure: "#b91c1c",
};

function project(points: MapPoint[], width: number, height: number) {
  if (points.length === 0) return [];
  const lats = points.map((p) => p.lat);
  const lngs = points.map((p) => p.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const pad = 28;
  const latSpan = Math.max(maxLat - minLat, 0.08);
  const lngSpan = Math.max(maxLng - minLng, 0.08);

  return points.map((point) => {
    const x = pad + ((point.lng - minLng) / lngSpan) * (width - pad * 2);
    const y =
      height - pad - ((point.lat - minLat) / latSpan) * (height - pad * 2);
    return { point, x, y };
  });
}

function renderSchematic(container: HTMLElement, model: MapModel): void {
  const width = Math.max(container.clientWidth || 480, 320);
  const height = Math.max(container.clientHeight || 280, 220);
  const projected = project(model.points, width, height);
  const path =
    projected.length >= 2
      ? projected.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ")
      : "";

  const markers = projected
    .map(({ point, x, y }) => {
      const color = point.color ?? ROLE_COLOR[point.role];
      return `
        <g>
          <circle cx="${x}" cy="${y}" r="8" fill="${color}" stroke="#fff" stroke-width="2" />
          <text x="${x + 12}" y="${y + 4}" font-size="12" font-family="Segoe UI,sans-serif" fill="#17221f">${point.label}</text>
        </g>
      `;
    })
    .join("");

  container.dataset.mapAdapter = "schematic";
  container.innerHTML = `
    <div class="schematic-map" aria-label="Corridor schematic map">
      <p class="schematic-map__badge">Schematic map · ${model.points.length} points</p>
      <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img">
        <defs>
          <linearGradient id="corridorFill" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#d7ebe1"/>
            <stop offset="55%" stop-color="#e8f1f7"/>
            <stop offset="100%" stop-color="#f4efe4"/>
          </linearGradient>
        </defs>
        <rect width="${width}" height="${height}" fill="url(#corridorFill)"/>
        <path d="M 24 ${height * 0.7} C ${width * 0.35} ${height * 0.2}, ${width * 0.65} ${height * 0.85}, ${width - 24} ${height * 0.35}"
          fill="none" stroke="#9fb8ab" stroke-width="10" stroke-linecap="round" opacity="0.55"/>
        ${path ? `<path d="${path}" fill="none" stroke="#146c52" stroke-width="3" stroke-dasharray="6 6"/>` : ""}
        ${markers}
      </svg>
    </div>
  `;
}

export class FakeMapAdapter implements MapAdapter {
  public mounted = false;
  public lastModel: MapModel | null = null;
  public destroyed = false;
  public calls: Array<"mount" | "update" | "destroy"> = [];
  private container: HTMLElement | null = null;

  mount(container: HTMLElement, model: MapModel): void {
    this.mounted = true;
    this.container = container;
    this.lastModel = model;
    this.calls.push("mount");
    renderSchematic(container, model);
  }

  update(model: MapModel): void {
    this.lastModel = model;
    this.calls.push("update");
    if (this.container) renderSchematic(this.container, model);
  }

  destroy(): void {
    this.destroyed = true;
    this.calls.push("destroy");
    if (this.container) {
      this.container.innerHTML = "";
      this.container = null;
    }
  }
}

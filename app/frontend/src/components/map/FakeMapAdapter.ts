import type { MapAdapter, MapModel, MapPoint } from "./types";

const NS = "http://www.w3.org/2000/svg";
const MAX_LABEL_CHARS = 18;
const LABEL_CHAR_PX = 6.5;
const LABEL_HEIGHT = 14;

const ROLE_COLOR: Record<MapPoint["role"], string> = {
  origin: "#0f766e",
  destination: "#1d4ed8",
  primary: "#146c52",
  backup: "#b45309",
  pressure: "#c23b22",
};

/** Short marker text for schematic SVG; full names stay in Station text list. */
export function schematicMarkerLabel(point: MapPoint): string {
  if (point.role === "pressure") return point.id;
  if (point.label.length <= MAX_LABEL_CHARS) return point.label;
  return `${point.label.slice(0, MAX_LABEL_CHARS - 1)}…`;
}

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

function boxesOverlap(
  a: { x: number; y: number; w: number; h: number },
  b: { x: number; y: number; w: number; h: number },
): boolean {
  return !(
    a.x + a.w < b.x ||
    b.x + b.w < a.x ||
    a.y + a.h < b.y ||
    b.y + b.h < a.y
  );
}

function placeLabels(
  projected: Array<{ point: MapPoint; x: number; y: number }>,
  width: number,
  height: number,
) {
  const placed: Array<{ x: number; y: number; w: number; h: number }> = [];

  return projected.map(({ point, x, y }) => {
    const text = schematicMarkerLabel(point);
    const w = Math.max(text.length * LABEL_CHAR_PX, 12);
    let labelX = Math.min(x + 12, width - w - 4);
    let labelY = y + 4;

    for (let step = 0; step < 12; step += 1) {
      const box = { x: labelX, y: labelY - 10, w, h: LABEL_HEIGHT };
      const hits = placed.some((other) => boxesOverlap(box, other));
      if (!hits && labelY < height - 4 && labelY > 12) {
        placed.push(box);
        return { point, x, y, labelX, labelY, text };
      }
      labelY += LABEL_HEIGHT;
      if (labelY > height - 8) {
        labelY = y + 4 - LABEL_HEIGHT * (step + 1);
        labelX = Math.max(4, x - w - 8);
      }
    }

    const fallback = { x: labelX, y: labelY - 10, w, h: LABEL_HEIGHT };
    placed.push(fallback);
    return { point, x, y, labelX, labelY, text };
  });
}

function el<K extends keyof SVGElementTagNameMap>(
  name: K,
  attrs: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) {
    node.setAttribute(key, String(value));
  }
  return node;
}

function renderSchematic(container: HTMLElement, model: MapModel): void {
  const width = Math.max(container.clientWidth || 480, 320);
  const height = Math.max(container.clientHeight || 280, 220);
  const projected = project(model.points, width, height);
  const labeled = placeLabels(projected, width, height);

  container.dataset.mapAdapter = "schematic";
  container.replaceChildren();

  const wrapper = document.createElement("div");
  wrapper.className = "schematic-map";
  wrapper.setAttribute("aria-label", "Corridor schematic map");

  const badge = document.createElement("p");
  badge.className = "schematic-map__badge";
  badge.textContent = `HCM–VT corridor · ${model.points.length} points`;
  wrapper.appendChild(badge);

  const svg = el("svg", {
    viewBox: `0 0 ${width} ${height}`,
    width: "100%",
    height: "100%",
    role: "img",
  });

  const defs = el("defs");
  const gradient = el("linearGradient", {
    id: "corridorFill",
    x1: "0",
    y1: "0",
    x2: "1",
    y2: "1",
  });
  gradient.appendChild(el("stop", { offset: "0%", "stop-color": "#d7ebe1" }));
  gradient.appendChild(el("stop", { offset: "55%", "stop-color": "#e8f1f7" }));
  gradient.appendChild(el("stop", { offset: "100%", "stop-color": "#f4efe4" }));
  defs.appendChild(gradient);
  svg.appendChild(defs);

  svg.appendChild(
    el("rect", {
      width,
      height,
      fill: "url(#corridorFill)",
    }),
  );
  svg.appendChild(
    el("path", {
      d: `M 24 ${height * 0.7} C ${width * 0.35} ${height * 0.2}, ${width * 0.65} ${height * 0.85}, ${width - 24} ${height * 0.35}`,
      fill: "none",
      stroke: "#9fb8ab",
      "stroke-width": 10,
      "stroke-linecap": "round",
      opacity: 0.55,
    }),
  );

  if (projected.length >= 2) {
    const d = projected
      .map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`)
      .join(" ");
    svg.appendChild(
      el("path", {
        d,
        fill: "none",
        stroke: "#146c52",
        "stroke-width": 3,
        "stroke-dasharray": "6 6",
      }),
    );
  }

  for (const { point, x, y, labelX, labelY, text } of labeled) {
    const group = el("g");
    const title = el("title");
    title.textContent = point.label;
    group.appendChild(title);
    group.appendChild(
      el("circle", {
        cx: x,
        cy: y,
        r: 8,
        fill: point.color ?? ROLE_COLOR[point.role],
        stroke: "#fff",
        "stroke-width": 2,
      }),
    );
    const label = el("text", {
      class: "schematic-map__label",
      x: labelX,
      y: labelY,
      "font-size": 11,
      "font-family": "IBM Plex Sans,Segoe UI,sans-serif",
      fill: "#17221f",
    });
    label.textContent = text;
    group.appendChild(label);
    svg.appendChild(group);
  }

  wrapper.appendChild(svg);
  container.appendChild(wrapper);
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
      this.container.replaceChildren();
      this.container = null;
    }
  }
}

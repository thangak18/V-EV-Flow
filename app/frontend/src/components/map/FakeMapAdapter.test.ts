import { describe, expect, test } from "vitest";

import { FakeMapAdapter, schematicMarkerLabel } from "./FakeMapAdapter";
import type { MapPoint } from "./types";

describe("FakeMapAdapter", () => {
  test("does not inject markup from point labels into the SVG DOM", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const adapter = new FakeMapAdapter();

    adapter.mount(container, {
      points: [
        {
          id: "x",
          lat: 10.5,
          lng: 106.8,
          label: '<script>alert(1)</script><circle id="injected"/>',
          role: "primary",
        },
      ],
    });

    expect(container.querySelector("#injected")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("text")?.textContent).not.toContain(
      "<circle",
    );
    adapter.destroy();
    container.remove();
  });

  test("uses short station ids for pressure markers and keeps full label in title", () => {
    const container = document.createElement("div");
    Object.defineProperty(container, "clientWidth", { value: 480 });
    Object.defineProperty(container, "clientHeight", { value: 280 });
    document.body.appendChild(container);
    const adapter = new FakeMapAdapter();

    const points: MapPoint[] = [
      {
        id: "S006",
        lat: 10.7,
        lng: 106.8,
        label: "Nhon Trach Service Area · pressure 0.40",
        role: "pressure",
      },
      {
        id: "S007",
        lat: 10.71,
        lng: 106.81,
        label: "Expressway Rest Stop Long Thanh-Dau Giay · pressure 0.50",
        role: "pressure",
      },
    ];

    adapter.mount(container, { points });

    const labels = Array.from(
      container.querySelectorAll("text.schematic-map__label"),
    ).map((node) => node.textContent);
    expect(labels).toEqual(["S006", "S007"]);
    // Full names stay in <title> for accessibility; visible SVG text is id-only.
    const titles = Array.from(container.querySelectorAll("title")).map(
      (node) => node.textContent,
    );
    expect(titles.some((t) => t?.includes("Nhon Trach Service Area"))).toBe(
      true,
    );
    expect(
      titles.some((t) =>
        t?.includes("Expressway Rest Stop Long Thanh-Dau Giay"),
      ),
    ).toBe(true);

    adapter.destroy();
    container.remove();
  });
});

describe("schematicMarkerLabel", () => {
  test("shortens long non-pressure labels", () => {
    expect(
      schematicMarkerLabel({
        id: "o",
        lat: 1,
        lng: 1,
        label: "Origin",
        role: "origin",
      }),
    ).toBe("Origin");
    expect(
      schematicMarkerLabel({
        id: "p",
        lat: 1,
        lng: 1,
        label: "Very Long Primary Station Name Here",
        role: "primary",
      }).length,
    ).toBeLessThanOrEqual(18);
  });
});

import { describe, expect, test } from "vitest";

import { FakeMapAdapter } from "./FakeMapAdapter";

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
    expect(container.textContent).toContain("<script>alert(1)</script>");
    adapter.destroy();
    container.remove();
  });
});

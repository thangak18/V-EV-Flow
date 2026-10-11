import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { FakeMapAdapter } from "./FakeMapAdapter";
import { MapView } from "./MapView";
import type { MapAdapter, MapModel } from "./types";

const model: MapModel = {
  points: [
    {
      id: "S012",
      lat: 10.5,
      lng: 106.8,
      label: "S012",
      role: "primary",
    },
    {
      id: "S015",
      lat: 10.4,
      lng: 107.0,
      label: "S015",
      role: "backup",
    },
  ],
};

describe("MapView", () => {
  test("mounts updates and destroys through the adapter", async () => {
    const adapter = new FakeMapAdapter();
    const { rerender, unmount } = render(
      <MapView model={model} adapterFactory={() => adapter} preferFake />,
    );

    await waitFor(() => expect(adapter.mounted).toBe(true));
    expect(adapter.lastModel?.points[0]?.role).toBe("primary");
    expect(screen.getByLabelText("Station text list")).toBeInTheDocument();

    const next = {
      ...model,
      points: [{ ...model.points[0]!, id: "S099", label: "S099" }],
    };
    rerender(
      <MapView model={next} adapterFactory={() => adapter} preferFake />,
    );
    await waitFor(() => expect(adapter.calls.includes("update")).toBe(true));

    unmount();
    expect(adapter.destroyed).toBe(true);
  });

  test("keeps textual list when adapter rejects", async () => {
    const failing: MapAdapter = {
      mount: () => Promise.reject(new Error("tiles blocked")),
      update: vi.fn(),
      destroy: vi.fn(),
    };

    render(<MapView model={model} adapterFactory={() => failing} preferFake />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /tiles blocked/i,
    );
    expect(screen.getByLabelText("Station text list")).toBeInTheDocument();
    expect(screen.getByText(/primary/i)).toBeInTheDocument();
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    expect(screen.getByText(/Trạm chính/i)).toBeInTheDocument();
  });

  test("applies the latest model after an async mount completes", async () => {
    let resolveMount: (() => void) | undefined;
    const updates: string[] = [];
    const slow: MapAdapter = {
      mount: () =>
        new Promise<void>((resolve) => {
          resolveMount = resolve;
        }),
      update: (next) => {
        updates.push(next.points[0]?.id ?? "");
      },
      destroy: vi.fn(),
    };

    const { rerender } = render(
      <MapView model={model} adapterFactory={() => slow} preferFake />,
    );

    const next = {
      ...model,
      points: [{ ...model.points[0]!, id: "LATEST", label: "LATEST" }],
    };
    rerender(<MapView model={next} adapterFactory={() => slow} preferFake />);
    resolveMount?.();

    await waitFor(() => expect(updates.at(-1)).toBe("LATEST"));
    expect(screen.getByLabelText("Station text list")).toHaveTextContent(
      "LATEST",
    );
  });
});

test("station information switches roles, closes, and reopens on a repeated focus", async () => {
  const adapter = new FakeMapAdapter();
  const factory = () => adapter;
  const { rerender } = render(
    <MapView
      model={{ ...model, focus: { id: "S012", role: "primary", sequence: 1 } }}
      adapterFactory={factory}
    />,
  );
  expect(await screen.findByTestId("station-map-info")).toHaveTextContent(
    "S012",
  );
  fireEvent.click(screen.getByRole("button", { name: "Đóng thông tin trạm" }));
  expect(screen.queryByTestId("station-map-info")).not.toBeInTheDocument();
  rerender(
    <MapView
      model={{ ...model, focus: { id: "S012", role: "primary", sequence: 2 } }}
      adapterFactory={factory}
    />,
  );
  expect(screen.getByTestId("station-map-info")).toHaveTextContent("S012");
  rerender(
    <MapView
      model={{ ...model, focus: { id: "S015", role: "backup", sequence: 3 } }}
      adapterFactory={factory}
    />,
  );
  expect(screen.getByTestId("station-map-info")).toHaveTextContent("S015");
  expect(screen.getByTestId("station-map-info")).toHaveTextContent(
    "TRẠM DỰ PHÒNG",
  );
  rerender(
    <MapView
      model={{
        ...model,
        points: [],
        focus: { id: "S015", role: "backup", sequence: 4 },
      }}
      adapterFactory={factory}
    />,
  );
  expect(screen.queryByTestId("station-map-info")).not.toBeInTheDocument();
});

test("retry recreates a failed map and preserves the station list", async () => {
  const destroy = vi.fn();
  let attempts = 0;
  const factory = () => ({
    mount: () =>
      ++attempts === 1
        ? Promise.reject(new Error("tiles blocked"))
        : Promise.resolve(),
    update: vi.fn(),
    destroy,
  });
  render(<MapView model={model} adapterFactory={factory} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("tiles blocked");
  fireEvent.click(screen.getByRole("button", { name: "Tải lại bản đồ" }));
  await waitFor(() =>
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(),
  );
  expect(attempts).toBe(2);
  expect(destroy).toHaveBeenCalled();
  expect(screen.getByLabelText("Station text list")).toBeInTheDocument();
});

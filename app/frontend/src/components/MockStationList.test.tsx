import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import type { Station } from "../services/api";
import { MockStationList } from "./MockStationList";

const station: Station = {
  station_id: "S001",
  name: "Demo station",
  lat: 10,
  lng: 106,
  n_ports: 4,
  power_kw: 120,
  connector_types: ["CCS2"],
  network: "phase0-demo",
  station_type: "urban",
  source: "fixture",
  assumptions: ["synthetic"],
};

describe("MockStationList", () => {
  test("renders a visible mock label and fixture station", async () => {
    const client = {
      listStations: vi.fn().mockResolvedValue({
        stations: [station],
        data_type: "mock",
        source_notes: [],
      }),
    };
    render(<MockStationList client={client} />);
    expect(await screen.findByText("S001")).toBeInTheDocument();
    expect(screen.getByText("Mock data")).toBeInTheDocument();
  });

  test("shows an empty state", async () => {
    const client = {
      listStations: vi.fn().mockResolvedValue({
        stations: [],
        data_type: "mock",
        source_notes: [],
      }),
    };
    render(<MockStationList client={client} />);
    expect(
      await screen.findByText("No stations are available yet."),
    ).toBeInTheDocument();
  });

  test("shows an error and retries", async () => {
    const client = {
      listStations: vi
        .fn()
        .mockRejectedValueOnce(new Error("Network unavailable"))
        .mockResolvedValue({
          stations: [station],
          data_type: "mock",
          source_notes: [],
        }),
    };
    render(<MockStationList client={client} />);
    expect(await screen.findByText("Network unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByText("S001")).toBeInTheDocument());
    expect(client.listStations).toHaveBeenCalledTimes(2);
  });

  test("aborts an old request before a replacement can update the list", async () => {
    let resolveFirst:
      | ((value: {
          stations: Station[];
          data_type: "mock";
          source_notes: string[];
        }) => void)
      | undefined;
    let firstSignal: AbortSignal | undefined;
    const firstClient = {
      listStations: vi.fn((signal?: AbortSignal) => {
        firstSignal = signal;
        return new Promise<{
          stations: Station[];
          data_type: "mock";
          source_notes: string[];
        }>((resolve) => {
          resolveFirst = resolve;
        });
      }),
    };
    const replacementStation = {
      ...station,
      station_id: "S002",
      name: "New station",
    };
    const replacementClient = {
      listStations: vi.fn().mockResolvedValue({
        stations: [replacementStation],
        data_type: "mock",
        source_notes: [],
      }),
    };
    const view = render(<MockStationList client={firstClient} />);

    view.rerender(<MockStationList client={replacementClient} />);
    expect(firstSignal?.aborted).toBe(true);
    resolveFirst?.({
      stations: [station],
      data_type: "mock",
      source_notes: [],
    });

    expect(await within(view.container).findByText("S002")).toBeInTheDocument();
    expect(within(view.container).queryByText("S001")).not.toBeInTheDocument();
  });
});

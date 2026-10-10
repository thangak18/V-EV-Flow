import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
});

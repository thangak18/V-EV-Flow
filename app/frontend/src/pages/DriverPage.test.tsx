import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { createMockApiClient } from "../test/mockApiClient";
import { DriverPage } from "./DriverPage";

const planResult = {
  request_id: "r1",
  primary: {
    station_id: "S012",
    eta: "2026-10-13T16:40:00+07:00",
    distance_km: 15,
    detour_km: 5,
    arrival_soc_pct: 15.5,
    p_available: 0.85,
  },
  backup: null,
  plan_p: 0.85,
  plan_p_assumption: "independent_stations",
  reasons: ["ok"],
  model_version: "v1",
  allocation_method: "ranking_penalty",
  data_type: "mock" as const,
  contract_version: "0.1.0",
};

describe("DriverPage", () => {
  test("calls recommend exactly once per explicit submit", async () => {
    const recommend = vi.fn().mockResolvedValue(planResult);
    const client = createMockApiClient({ recommend });

    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    expect(recommend).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    await waitFor(() => expect(recommend).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("S012")).toBeInTheDocument();
  });

  test("reversing corridor preset updates map origin and destination", async () => {
    const client = createMockApiClient();
    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    expect(screen.getByLabelText("Station text list")).toHaveTextContent(
      "10.7800",
    );
    fireEvent.change(screen.getByLabelText("Route"), {
      target: { value: "vt_hcm" },
    });
    await waitFor(() => {
      const list = screen.getByLabelText("Station text list");
      expect(list).toHaveTextContent("origin");
      expect(list.textContent).toMatch(/10\.3500/);
      expect(list.textContent).toMatch(/107\.0800/);
    });
  });

  test("does not invent map coordinates when station is missing from directory", async () => {
    const recommend = vi.fn().mockResolvedValue(planResult);
    const client = createMockApiClient({ recommend });

    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(
      await screen.findByText(/location unavailable/i),
    ).toBeInTheDocument();
    const list = screen.getByLabelText("Station text list");
    expect(list.textContent).toContain("S012");
    expect(list.textContent).not.toMatch(/10\.5500/);
    expect(list.textContent).not.toMatch(/106\.9000/);
  });

  test("clears previous recommendation when corridor preset changes", async () => {
    const recommend = vi.fn().mockResolvedValue(planResult);
    const client = createMockApiClient({ recommend });

    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(await screen.findByText("S012")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Route"), {
      target: { value: "vt_hcm" },
    });
    await waitFor(() => {
      expect(screen.queryByText("S012")).not.toBeInTheDocument();
      expect(
        screen.getByText(/Submit a request to begin/i),
      ).toBeInTheDocument();
    });
  });

  test("shows directory failure notice when listStations errors", async () => {
    const client = createMockApiClient({
      listStations: vi.fn().mockRejectedValue(new Error("directory down")),
    });

    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    expect(
      await screen.findByText(/Station directory unavailable/i),
    ).toBeInTheDocument();
  });
});

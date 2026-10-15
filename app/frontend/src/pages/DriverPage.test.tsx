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
  test("labels the directory source before submit and the prediction source afterwards", async () => {
    const client = createMockApiClient({
      listStations: vi.fn().mockResolvedValue({
        stations: [],
        data_type: "simulated",
        source_notes: [],
      }),
      recommend: vi
        .fn()
        .mockResolvedValue({ ...planResult, data_type: "mixed" }),
    });
    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );
    expect(await screen.findByText("Dữ liệu mô phỏng")).toBeInTheDocument();
    expect(screen.queryByText("Dữ liệu minh họa")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(await screen.findByText("Dữ liệu hỗn hợp")).toBeInTheDocument();
    expect(screen.queryByText("Dữ liệu mô phỏng")).not.toBeInTheDocument();
  });

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
    fireEvent.change(screen.getByLabelText("Điểm đi"), {
      target: { value: "Vũng Tàu" },
    });
    fireEvent.change(screen.getByLabelText("Điểm đến"), {
      target: { value: "TP. Hồ Chí Minh" },
    });
    await waitFor(() => {
      const list = screen.getByLabelText("Station text list");
      expect(list).toHaveTextContent("Điểm đi");
      expect(list).toHaveTextContent("Vũng Tàu");
      expect(list).toHaveTextContent("TP. Hồ Chí Minh");
      expect(list.textContent).toMatch(/10\.3500/);
      expect(list.textContent).toMatch(/107\.0800/);
      // Origin of vt_hcm is Vũng Tàu coords; destination is HCMC coords.
      expect(list.textContent).toMatch(
        /Điểm đi: Vũng Tàu \(10\.3500, 107\.0800\)/,
      );
      expect(list.textContent).toMatch(
        /Điểm đến: TP\. Hồ Chí Minh \(10\.7800, 106\.7000\)/,
      );
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
    expect(await screen.findByText(/chưa có tọa độ/i)).toBeInTheDocument();
    const list = screen.getByLabelText("Station text list");
    expect(list.textContent).toContain("S012");
    expect(list.textContent).not.toMatch(/10\.5500/);
    expect(list.textContent).not.toMatch(/106\.9000/);
  });

  test("pipeline-shaped plan: directory coords, backup, simulated badge", async () => {
    const recommend = vi.fn().mockResolvedValue({
      ...planResult,
      primary: {
        station_id: "S012",
        eta: "2026-10-13T16:40:00+07:00",
        distance_km: 15,
        detour_km: 5,
        arrival_soc_pct: 15.5,
        p_available: 0.85,
      },
      backup: {
        station_id: "S013",
        eta: "2026-10-13T16:55:00+07:00",
        distance_km: 25,
        detour_km: 7.5,
        arrival_soc_pct: 12.5,
        p_available: 0.6,
      },
      data_type: "simulated" as const,
      reasons: ["pipeline ok"],
    });
    const client = createMockApiClient({
      recommend,
      listStations: vi.fn().mockResolvedValue({
        stations: [
          {
            station_id: "S012",
            name: "Long Dien Crossing",
            lat: 10.48,
            lng: 107.21,
            n_ports: 4,
            power_kw: 60,
            connector_types: ["CCS2"],
            network: "phase0-demo",
            station_type: "highway",
            source: "phase0-fixture",
            assumptions: [],
          },
          {
            station_id: "S013",
            name: "Vung Tau Back Beach",
            lat: 10.37,
            lng: 107.11,
            n_ports: 6,
            power_kw: 120,
            connector_types: ["CCS2"],
            network: "phase0-demo",
            station_type: "urban",
            source: "phase0-fixture",
            assumptions: [],
          },
        ],
        data_type: "mock",
        source_notes: [],
      }),
    });

    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(await screen.findByTestId("plan-hero")).toHaveTextContent(
      "Long Dien Crossing",
    );
    expect(screen.getByTestId("plan-hero")).toHaveTextContent("85%");
    expect(screen.getByTestId("plan-hero")).toHaveTextContent(/16:40/);
    expect(screen.getByText("Dữ liệu mô phỏng")).toBeInTheDocument();
    expect(screen.getAllByText("Trạm dự phòng").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(
      screen.getAllByText("Vung Tau Back Beach").length,
    ).toBeGreaterThanOrEqual(1);
    const list = screen.getByLabelText("Station text list");
    expect(list.textContent).toMatch(/10\.4800/);
    expect(list.textContent).toMatch(/107\.2100/);
    expect(list.textContent).toMatch(/10\.3700/);
    expect(list.textContent).not.toMatch(/chưa có tọa độ/i);
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

    fireEvent.change(screen.getByLabelText("Điểm đi"), {
      target: { value: "Vũng Tàu" },
    });
    fireEvent.change(screen.getByLabelText("Điểm đến"), {
      target: { value: "TP. Hồ Chí Minh" },
    });
    await waitFor(() => {
      expect(screen.queryByText("S012")).not.toBeInTheDocument();
      expect(screen.getByText(/Chưa tìm trạm sạc/i)).toBeInTheDocument();
    });
  });

  test("selects directory locations, sends their coordinates, and rejects unselected drafts", async () => {
    const recommend = vi.fn().mockResolvedValue(planResult);
    const client = createMockApiClient({
      recommend,
      listStations: vi
        .fn()
        .mockResolvedValue({
          stations: [
            { station_id: "S099", name: "Long Thành", lat: 10.8, lng: 107.01 },
          ],
          data_type: "simulated",
          source_notes: [],
        }),
    });
    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <DriverPage />
        </MemoryRouter>
      </ApiProvider>,
    );
    await waitFor(() =>
      expect(
        document.querySelector('option[value="Long Thành (S099)"]'),
      ).toBeInTheDocument(),
    );
    const origin = screen.getByLabelText("Điểm đi");
    const destination = screen.getByLabelText("Điểm đến");
    const submit = screen.getByRole("button", { name: /Tìm kế hoạch sạc/i });
    fireEvent.change(origin, { target: { value: "địa chỉ chưa chọn" } });
    expect(submit).toBeDisabled();
    expect(screen.getByLabelText("Station text list")).not.toHaveTextContent(
      "Điểm đi:",
    );
    fireEvent.change(origin, { target: { value: "Long Thành (S099)" } });
    fireEvent.change(destination, { target: { value: "Long Thành (S099)" } });
    expect(submit).toBeDisabled();
    fireEvent.change(destination, { target: { value: "TP. Hồ Chí Minh" } });
    fireEvent.click(submit);
    await waitFor(() => expect(recommend).toHaveBeenCalledTimes(1));
    expect(recommend.mock.calls[0]![0]).toMatchObject({
      origin: { lat: 10.8, lng: 107.01 },
      destination: { lat: 10.78, lng: 106.7 },
    });
    expect(screen.getByLabelText("Station text list")).toHaveTextContent(
      "Điểm đi: Long Thành (S099) (10.8000, 107.0100)",
    );
    expect(await screen.findByText("S012")).toBeInTheDocument();
    fireEvent.change(destination, { target: { value: "" } });
    expect(screen.queryByText("S012")).not.toBeInTheDocument();
    expect(submit).toBeDisabled();
    expect(recommend).toHaveBeenCalledTimes(1);
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
      await screen.findByText(/Không tải được danh mục trạm/i),
    ).toBeInTheDocument();
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { createMockApiClient } from "../test/mockApiClient";
import { DriverPage } from "./DriverPage";

describe("DriverPage", () => {
  test("calls recommend exactly once per explicit submit", async () => {
    const recommend = vi.fn().mockResolvedValue({
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
      data_type: "mock",
      contract_version: "0.1.0",
    });

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
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { createMockApiClient } from "../test/mockApiClient";
import { OperatorPage } from "./OperatorPage";

describe("OperatorPage", () => {
  test("loads pressure on explicit apply and runs three simulations", async () => {
    const getPressure = vi.fn().mockResolvedValue({
      time: "2026-10-13T16:00:00+07:00",
      scenario: "tet",
      contract_version: "0.1.0",
      stations: [
        {
          station_id: "S001",
          p_available: 0.4,
          pressure_score: 0.6,
          data_type: "mock",
        },
      ],
    });
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string }) => ({
        scenario: "tet",
        seed: 42,
        strategy: body.strategy,
        model_version: "fake-sim-v1",
        fixture_hash: "phase0-fixture-hash",
        contract_version: "0.1.0",
        metrics: {
          success_rate: 0.9,
          mean_detour_km: 2,
          mean_wait_minutes: 3,
          failed_count: 10,
          vehicle_count: 100,
        },
      }));

    const client = createMockApiClient({
      getPressure,
      pressure: getPressure,
      simulate,
    });

    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <OperatorPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    fireEvent.change(screen.getByLabelText("Scenario"), {
      target: { value: "tet" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Apply scenario/i }));
    await waitFor(() => expect(getPressure).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/pressure 0\.60/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Pressure legend")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /Compare 3 strategies/i }),
    );
    await waitFor(() => expect(simulate).toHaveBeenCalledTimes(3));
    expect(screen.getByText("Nearest")).toBeInTheDocument();
  });
});

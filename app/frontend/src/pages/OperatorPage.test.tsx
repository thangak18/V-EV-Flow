import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { ApiProvider } from "../app/ApiContext";
import { FIXTURE_HASH } from "../test/fixtureHash";
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
        fixture_hash: FIXTURE_HASH,
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

    fireEvent.change(screen.getByLabelText("Kịch bản"), {
      target: { value: "tet" },
    });
    fireEvent.click(
      await screen.findByRole("button", { name: /Áp dụng kịch bản/i }),
    );
    await waitFor(() => expect(getPressure).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/áp lực 0\.60/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Chú thích áp lực")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /So sánh 3 chiến lược/i }),
    );
    await waitFor(() => expect(simulate).toHaveBeenCalledTimes(3));
    expect(screen.getAllByText("Gần nhất").length).toBeGreaterThanOrEqual(1);
  });

  test("compare leaders follow runner rates without a fixed winner", async () => {
    const getPressure = vi.fn().mockResolvedValue({
      time: "2026-10-13T16:00:00+07:00",
      scenario: "normal",
      contract_version: "0.1.0",
      stations: [
        {
          station_id: "S001",
          p_available: 0.4,
          pressure_score: 0.6,
          data_type: "simulated",
        },
      ],
    });
    const rates: Record<string, number> = {
      nearest: 0.8,
      currently_available: 0.85,
      ai_allocation: 0.92,
    };
    const simulate = vi
      .fn()
      .mockImplementation(async (body: { strategy: string }) => ({
        scenario: "normal",
        seed: 42,
        strategy: body.strategy,
        model_version: "runner-v1",
        fixture_hash: FIXTURE_HASH,
        contract_version: "0.1.0",
        metrics: {
          success_rate: rates[body.strategy] ?? 0.5,
          mean_detour_km: 2,
          mean_wait_minutes: 3,
          failed_count: Math.round(100 * (1 - (rates[body.strategy] ?? 0.5))),
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

    fireEvent.click(
      await screen.findByRole("button", { name: /Áp dụng kịch bản/i }),
    );
    expect(await screen.findByText("Dữ liệu mô phỏng")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /So sánh 3 chiến lược/i }),
    );
    await waitFor(() => expect(simulate).toHaveBeenCalledTimes(3));
    expect(screen.getByTestId("strategy-delta")).toHaveTextContent(
      /Phân bổ AI/i,
    );
    expect(screen.getByTestId("strategy-delta")).toHaveTextContent(
      /12\.0 điểm %/,
    );
    expect(screen.getByText(/Không chọn sẵn người thắng/)).toBeInTheDocument();
    expect(screen.getByText(/100 xe/)).toBeInTheDocument();
  });

  test("keeps pressure stations textual when directory lacks coordinates", async () => {
    const getPressure = vi.fn().mockResolvedValue({
      time: "2026-10-13T16:00:00+07:00",
      scenario: "normal",
      contract_version: "0.1.0",
      stations: [
        {
          station_id: "UNKNOWN",
          p_available: 0.2,
          pressure_score: 0.8,
          data_type: "mock",
        },
      ],
    });
    const client = createMockApiClient({
      listStations: vi.fn().mockResolvedValue({
        stations: [],
        data_type: "mock",
        source_notes: [],
      }),
      getPressure,
      pressure: getPressure,
    });

    render(
      <ApiProvider client={client}>
        <MemoryRouter>
          <OperatorPage />
        </MemoryRouter>
      </ApiProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: /Áp dụng kịch bản/i }),
    );
    expect(await screen.findByText(/chưa có tọa độ/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Station text list")).toHaveTextContent(
      "UNKNOWN",
    );
    expect(screen.getByLabelText("Station text list").textContent).not.toMatch(
      /10\.7800/,
    );
  });
});

test("what-if uses the current valid seed/count drafts and blocks invalid drafts", async () => {
  const { whatIfFixture } = await import("../test/p1Fixtures");
  const whatif = vi
    .fn()
    .mockImplementation(
      async (body: import("../services/api").WhatIfRequest) => ({
        ...whatIfFixture,
        change: body.change,
        before: {
          ...whatIfFixture.before,
          scenario: body.scenario,
          seed: body.seed,
          strategy: body.strategy,
          metrics: {
            ...whatIfFixture.before.metrics,
            vehicle_count: body.vehicle_count,
            failed_count: Math.floor(body.vehicle_count * 0.1),
          },
        },
        after: {
          ...whatIfFixture.after,
          scenario: body.scenario,
          seed: body.seed,
          strategy: body.strategy,
          metrics: {
            ...whatIfFixture.after.metrics,
            vehicle_count: body.vehicle_count,
            failed_count: Math.floor(body.vehicle_count * 0.05),
          },
        },
      }),
    );
  render(
    <ApiProvider client={createMockApiClient({ whatif })}>
      <MemoryRouter>
        <OperatorPage />
      </MemoryRouter>
    </ApiProvider>,
  );
  const button = screen.getByRole("button", { name: "So sánh trước / sau" });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Seed (mầm ngẫu nhiên)"), {
    target: { value: "91" },
  });
  fireEvent.change(screen.getByLabelText("Số xe"), { target: { value: "50" } });
  fireEvent.click(button);
  await waitFor(() =>
    expect(whatif).toHaveBeenCalledWith(
      expect.objectContaining({ seed: 91, vehicle_count: 50 }),
    ),
  );
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Seed (mầm ngẫu nhiên)"), {
    target: { value: "" },
  });
  expect(button).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Seed (mầm ngẫu nhiên)"), {
    target: { value: "1.5" },
  });
  expect(button).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Seed (mầm ngẫu nhiên)"), {
    target: { value: "-1" },
  });
  expect(button).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Seed (mầm ngẫu nhiên)"), {
    target: { value: "0" },
  });
  expect(button).toBeEnabled();
});

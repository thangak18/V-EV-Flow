import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { StrategyRow } from "../../hooks/useSimulationComparison";
import { StrategyComparison } from "./StrategyComparison";

const rows: StrategyRow[] = [
  {
    strategy: "nearest",
    status: "success",
    result: {
      scenario: "tet",
      seed: 42,
      strategy: "nearest",
      model_version: "fake-sim-v1",
      fixture_hash: "phase0-fixture-hash",
      contract_version: "0.1.0",
      metrics: {
        success_rate: 0.9,
        mean_detour_km: 2.5,
        mean_wait_minutes: 4,
        failed_count: 10,
        vehicle_count: 100,
      },
    },
  },
  {
    strategy: "currently_available",
    status: "error",
    message: "timeout",
  },
  {
    strategy: "ai_allocation",
    status: "success",
    result: {
      scenario: "tet",
      seed: 42,
      strategy: "ai_allocation",
      model_version: "fake-sim-v1",
      fixture_hash: "phase0-fixture-hash",
      contract_version: "0.1.0",
      metrics: {
        success_rate: 0.92,
        mean_detour_km: 2.1,
        mean_wait_minutes: 3.5,
        failed_count: 8,
        vehicle_count: 100,
      },
    },
  },
];

describe("StrategyComparison", () => {
  test("shows metrics and preserves partial failures", () => {
    render(
      <StrategyComparison
        rows={rows}
        meta={{ scenario: "tet", seed: 42, vehicleCount: 100 }}
      />,
    );
    expect(screen.getByText("Nearest")).toBeInTheDocument();
    expect(screen.getByText("90.0%")).toBeInTheDocument();
    expect(screen.getByText(/Failed: timeout/)).toBeInTheDocument();
    expect(screen.getByText(/No hard-coded winner/)).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });
});

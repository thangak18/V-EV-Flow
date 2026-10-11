import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { RecommendationResult } from "../../services/api";
import { PlanSummary } from "./PlanSummary";

const base: RecommendationResult = {
  request_id: "demo-001",
  primary: {
    station_id: "S012",
    eta: "2026-10-13T16:40:00+07:00",
    distance_km: 15,
    detour_km: 5,
    arrival_soc_pct: 15.5,
    p_available: 0.854,
  },
  backup: {
    station_id: "S015",
    eta: "2026-10-13T16:55:00+07:00",
    distance_km: 25,
    detour_km: 7.5,
    arrival_soc_pct: 12.5,
    p_available: 0.6,
  },
  plan_p: 0.94,
  plan_p_assumption: "independent_stations",
  reasons: ["Đủ pin để tới trạm chính"],
  time_shift: null,
  model_version: "example-v1",
  allocation_method: "ranking_penalty",
  data_type: "mock",
  contract_version: "0.1.0",
};

describe("PlanSummary", () => {
  test("renders primary backup probability and assumptions", () => {
    render(<PlanSummary result={base} />);
    expect(screen.getByText("Primary")).toBeInTheDocument();
    expect(screen.getByText("Backup")).toBeInTheDocument();
    expect(screen.getByText("S012")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText(/15\.5%/)).toBeInTheDocument();
    expect(screen.getByText(/independent_stations/)).toBeInTheDocument();
    expect(screen.getByText("Mock data")).toBeInTheDocument();
    expect(screen.getByText("Đủ pin để tới trạm chính")).toBeInTheDocument();
    expect(screen.getByText(/example-v1/)).toBeInTheDocument();
  });

  test("handles missing backup and no-plan reasons", () => {
    render(
      <PlanSummary
        result={{
          ...base,
          primary: null,
          backup: null,
          plan_p: null,
          reasons: ["Không còn trạm khả thi"],
        }}
      />,
    );
    expect(screen.getByText(/No feasible station/i)).toBeInTheDocument();
    expect(screen.getByText("Không còn trạm khả thi")).toBeInTheDocument();
  });
});

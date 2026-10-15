import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { StrategyRow } from "../../hooks/useSimulationComparison";
import { FIXTURE_HASH } from "../../test/fixtureHash";
import { StrategyComparison, topSuccessRows } from "./StrategyComparison";

function successRow(
  strategy: StrategyRow["strategy"],
  successRate: number,
): Extract<StrategyRow, { status: "success" }> {
  return {
    strategy,
    status: "success",
    result: {
      scenario: "tet",
      seed: 42,
      strategy,
      model_version: "fake-sim-v1",
      fixture_hash: FIXTURE_HASH,
      contract_version: "0.1.0",
      metrics: {
        success_rate: successRate,
        mean_detour_km: 2.5,
        mean_wait_minutes: 4,
        failed_count: 10,
        vehicle_count: 100,
      },
    },
  };
}

const rows: StrategyRow[] = [
  successRow("nearest", 0.9),
  {
    strategy: "currently_available",
    status: "error",
    message: "timeout",
  },
  successRow("ai_allocation", 0.92),
];

describe("StrategyComparison", () => {
  test("labels fake simulation as mock", () => {
    render(<StrategyComparison rows={[successRow("nearest", 0.9)]} />);
    expect(screen.getByTestId("simulation-source")).toHaveTextContent("mock");
    expect(screen.getByTestId("simulation-source")).toHaveTextContent(
      "chưa chạy simulator thực",
    );
  });

  test("labels stateful comparison and background model snapshots", () => {
    const baseline = successRow("nearest", 0.9);
    const ai = successRow("ai_allocation", 0.92);
    baseline.result.model_version = "simulated-baseline-v1";
    ai.result.model_version = "lightgbm-test";
    render(<StrategyComparison rows={[baseline, ai]} />);
    expect(screen.getByTestId("simulation-source")).toHaveTextContent(
      "simulated",
    );
    expect(screen.getByTestId("simulation-source")).toHaveTextContent(
      "lịch sử nền",
    );
  });

  test("shows bars with delta and keeps tech details collapsed", () => {
    render(
      <StrategyComparison
        rows={rows}
        meta={{ scenario: "tet", seed: 42, vehicleCount: 100 }}
      />,
    );
    expect(screen.getAllByText("Gần nhất").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("90.0%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("strategy-delta")).toHaveTextContent(
      /Phân bổ AI/i,
    );
    expect(screen.getAllByText(/Lỗi: timeout/).length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByText(/So sánh cùng nhóm xe/)).toBeInTheDocument();
    expect(screen.getAllByText("10").length).toBeGreaterThanOrEqual(1);
    const tech = screen.getByText("Chi tiết mô phỏng").closest("details");
    expect(tech).not.toHaveAttribute("open");
  });

  test("marks all tied leaders without picking array order", () => {
    const tied: StrategyRow[] = [
      successRow("nearest", 0.9),
      successRow("currently_available", 0.9),
      successRow("ai_allocation", 0.9),
    ];
    render(<StrategyComparison rows={tied} />);
    expect(screen.getByTestId("strategy-delta")).toHaveTextContent(
      /Đồng hạng/i,
    );
    expect(screen.getByTestId("strategy-delta")).toHaveTextContent(/Gần nhất/);
    expect(screen.getByTestId("strategy-delta")).toHaveTextContent(
      /Đang trống/,
    );
    expect(screen.getByTestId("strategy-delta")).toHaveTextContent(
      /Phân bổ AI/,
    );
    expect(screen.getAllByText(/đồng hạng/i).length).toBeGreaterThanOrEqual(3);
    expect(
      topSuccessRows(
        tied.filter(
          (row): row is Extract<StrategyRow, { status: "success" }> =>
            row.status === "success",
        ),
      ),
    ).toHaveLength(3);
  });
});

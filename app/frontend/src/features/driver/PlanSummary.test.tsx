import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { RecommendationResult } from "../../services/api";
import { formatEtaTime, PlanEmptyState, PlanSummary } from "./PlanSummary";

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
  test("does not round near certainty into a false 0 or 100 percent", () => {
    render(
      <PlanSummary
        result={{
          ...base,
          primary: { ...base.primary!, p_available: 0.999 },
          backup: { ...base.backup!, p_available: 0.001 },
          plan_p: 0.9999,
        }}
      />,
    );
    expect(screen.getAllByText(">99%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("<1%")).toBeInTheDocument();
    expect(screen.queryByText("100%")).not.toBeInTheDocument();
  });

  test("renders hero focus primary backup and hides tech until details open", () => {
    render(
      <PlanSummary
        result={base}
        stationNames={{ S012: "Trạm Long Thành", S015: "Trạm Phú Mỹ" }}
      />,
    );
    expect(screen.getByTestId("plan-hero")).toBeInTheDocument();
    expect(screen.getByText("Trạm Long Thành")).toBeInTheDocument();
    expect(screen.getAllByText("85%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Xem trạm trên bản đồ/i)).toBeInTheDocument();
    expect(screen.getByText("Trạm dự phòng")).toBeInTheDocument();
    expect(screen.getByText(/15,5%/)).toBeInTheDocument();
    expect(screen.getByText("Đủ pin để tới trạm chính")).toBeInTheDocument();
    expect(screen.getByText(/giả định hai trạm độc lập/i)).toBeInTheDocument();
    expect(screen.getByText(/16:40/)).toBeInTheDocument();

    const details = screen
      .getByText("Cách tính & độ tin cậy")
      .closest("details");
    expect(details).not.toHaveAttribute("open");
    details?.setAttribute("open", "");
    expect(screen.getByText(/example-v1/)).toBeInTheDocument();
  });

  test("formats ETA in Asia/Ho_Chi_Minh regardless of host timezone", () => {
    expect(formatEtaTime("2026-10-13T16:40:00+07:00")).toMatch(/16:40/);
    // Same instant in UTC must still render Vietnam local clock.
    expect(formatEtaTime("2026-10-13T09:40:00Z")).toMatch(/16:40/);
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
    expect(screen.getByText(/Không có trạm khả thi/i)).toBeInTheDocument();
    expect(screen.getByText("Không còn trạm khả thi")).toBeInTheDocument();
  });

  test("empty state copy matches dashboard idle", () => {
    render(<PlanEmptyState />);
    expect(screen.getByText("Chưa tìm trạm sạc")).toBeInTheDocument();
    expect(screen.getByText(/Kết quả sẽ hiện tại đây/i)).toBeInTheDocument();
  });
});

test("displays a non-binding time-shift estimate without changing the current plan", () => {
  render(
    <PlanSummary
      result={{
        ...base,
        time_shift: 15,
        time_shift_estimate: {
          minutes: 15,
          station_id: "S012",
          depart_time: "2026-10-13T16:15:00+07:00",
          eta: "2026-10-13T16:55:00+07:00",
          p_available: 0.95,
          improvement: 0.096,
          assumptions: ["Giữ snapshot hiện tại"],
        },
      }}
    />,
  );
  expect(screen.getByTestId("time-shift-suggestion")).toHaveTextContent(
    "Khởi hành muộn 15 phút",
  );
  expect(screen.getByTestId("time-shift-suggestion")).toHaveTextContent(
    "chưa đổi kế hoạch hoặc ghi thêm phân bổ",
  );
  expect(screen.getByTestId("plan-hero")).toContainHTML(
    'data-probability="0.854"',
  );
});

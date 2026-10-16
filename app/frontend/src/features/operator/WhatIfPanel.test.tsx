import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ApiProvider } from "../../app/ApiContext";
import { ApiError, type Station } from "../../services/api";
import { createMockApiClient } from "../../test/mockApiClient";
import { whatIfFixture } from "../../test/p1Fixtures";
import { WhatIfPanel } from "./WhatIfPanel";
const station: Station = {
  station_id: "S001",
  name: "Trạm thử",
  lat: 10.78,
  lng: 106.7,
  n_ports: 4,
  power_kw: 120,
  connector_types: ["CCS2"],
  network: "test",
  station_type: "urban",
  source: "test",
  assumptions: [],
};

test("what-if is explicit and shows an honest before/after comparison", async () => {
  const whatif = vi.fn().mockResolvedValue(whatIfFixture);
  render(
    <ApiProvider client={createMockApiClient({ whatif })}>
      <WhatIfPanel
        scenario="tet"
        seed={42}
        vehicleCount={100}
        stations={[station]}
      />
    </ApiProvider>,
  );
  expect(whatif).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "So sánh trước / sau" }));
  expect(await screen.findByTestId("whatif-result")).toHaveTextContent(
    "100 xe · mã lần chạy 42",
  );
  expect(whatif).toHaveBeenCalledWith(
    expect.objectContaining({
      seed: 42,
      vehicle_count: 100,
      change: { kind: "add_ports", station_id: "S001", ports: 2 },
    }),
  );
  expect(
    screen.getByText(/Dự báo vẫn dùng cấu hình trạm ban đầu/),
  ).toBeInTheDocument();
  expect(
    screen.getByText("80.0%", { selector: ".whatif-value" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText("90.0%", { selector: ".whatif-value" }),
  ).toBeInTheDocument();
});

test("shift preset sends exactly the declared fraction and displays actual shifted count", async () => {
  const result = {
    ...whatIfFixture,
    change: {
      kind: "shift_departures" as const,
      fraction: 0.2,
      target_hour: 21,
    },
    shifted_vehicle_count: 20,
  };
  const whatif = vi.fn().mockResolvedValue(result);
  render(
    <ApiProvider client={createMockApiClient({ whatif })}>
      <WhatIfPanel
        scenario="tet"
        seed={42}
        vehicleCount={100}
        stations={[station]}
      />
    </ApiProvider>,
  );
  fireEvent.click(
    screen.getByRole("radio", { name: /Chuyển xe sang giờ thấp điểm/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "So sánh trước / sau" }));
  expect(await screen.findByTestId("whatif-result")).toHaveTextContent(
    "Đã dịch 20 xe",
  );
  expect(whatif).toHaveBeenCalledWith(
    expect.objectContaining({ change: result.change }),
  );
  const schedule = screen.getByRole("region", {
    name: "So sánh lịch xuất phát",
  });
  expect(schedule).toHaveTextContent("80 xe giữ lịch gốc");
  expect(schedule).toHaveTextContent("20 xe chuyển sang 21h");
  expect(
    screen.queryByRole("button", { name: "Trước thay đổi" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Station text list")).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("Xem 1 trạm trong phạm vi áp dụng"));
  expect(await screen.findByLabelText("Station text list")).toHaveTextContent(
    "Trạm thử · 4 cổng",
  );
});

test("invalid experiment parameters block submission", () => {
  const whatif = vi.fn();
  render(
    <ApiProvider client={createMockApiClient({ whatif })}>
      <WhatIfPanel
        scenario="tet"
        seed={-1}
        vehicleCount={0}
        stations={[station]}
      />
    </ApiProvider>,
  );
  expect(
    screen.getByRole("button", { name: "So sánh trước / sau" }),
  ).toBeDisabled();
  expect(whatif).not.toHaveBeenCalled();
});

test("failed what-if exposes retry instead of fabricated metrics", async () => {
  const whatif = vi
    .fn()
    .mockRejectedValueOnce(
      new ApiError(503, "FEATURE_NOT_READY", "unavailable", null),
    )
    .mockResolvedValueOnce(whatIfFixture);
  render(
    <ApiProvider client={createMockApiClient({ whatif })}>
      <WhatIfPanel
        scenario="tet"
        seed={42}
        vehicleCount={100}
        stations={[station]}
      />
    </ApiProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "So sánh trước / sau" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "chưa hỗ trợ đánh giá phương án",
  );
  expect(screen.queryByTestId("whatif-result")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "So sánh trước / sau" }));
  expect(await screen.findByTestId("whatif-result")).toBeInTheDocument();
});

test("what-if map toggles actual port counts and clears obsolete experiment results", async () => {
  const client = createMockApiClient({
    whatif: vi.fn().mockResolvedValue(whatIfFixture),
  });
  const view = (seed: number) => (
    <ApiProvider client={client}>
      <WhatIfPanel
        scenario="tet"
        seed={seed}
        vehicleCount={100}
        stations={[station]}
      />
    </ApiProvider>
  );
  const { rerender } = render(view(42));
  fireEvent.click(screen.getByRole("button", { name: "So sánh trước / sau" }));
  const map = await screen.findByLabelText("Bản đồ so sánh phương án");
  expect(map).toHaveTextContent("Trạm thử · 6 cổng");
  fireEvent.click(screen.getByRole("button", { name: "Trước thay đổi" }));
  expect(map).toHaveTextContent("Trạm thử · 4 cổng");
  expect(map).toHaveTextContent("80.0%");
  rerender(view(43));
  expect(
    screen.queryByLabelText("Bản đồ so sánh phương án"),
  ).not.toBeInTheDocument();
});

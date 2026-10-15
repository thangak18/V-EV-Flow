import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test, vi } from "vitest";

import { ApiError, type ApiClient } from "../services/api";
import { createMockApiClient } from "../test/mockApiClient";
import { ApiProvider } from "./ApiContext";
import { AppRouter } from "./router";

const plan = {
  request_id: "reset-check",
  primary: {
    station_id: "S001",
    eta: "2026-10-13T16:05:00+07:00",
    distance_km: 1.062,
    detour_km: 1.348,
    arrival_soc_pct: 19.68,
    p_available: 0.96,
  },
  backup: null,
  plan_p: 0.96,
  plan_p_assumption: null,
  reasons: ["Đủ pin"],
  time_shift: null,
  model_version: "lightgbm-test",
  allocation_method: "heuristic_ranking",
  data_type: "simulated",
  contract_version: "0.1.0",
};
function mount(client: ApiClient) {
  return render(
    <ApiProvider client={client}>
      <MemoryRouter initialEntries={["/driver"]}>
        <AppRouter />
      </MemoryRouter>
    </ApiProvider>,
  );
}

test("discloses route and prediction mode without automatically allocating", async () => {
  const client = createMockApiClient({
    ready: vi.fn().mockResolvedValue({
      ready: true,
      data_backend: "file",
      predictor_backend: "model",
      route_backend: "goong",
    }),
  });
  mount(client);
  expect(
    await screen.findByText(/Chỉ đường tài xế: Goong.*Mô hình đã huấn luyện/),
  ).toBeInTheDocument();
  expect(client.recommend).not.toHaveBeenCalled();
});

test("discloses unknown readiness instead of claiming Goong or model is available", async () => {
  mount(
    createMockApiClient({
      ready: vi.fn().mockRejectedValue(new Error("offline")),
    }),
  );
  expect(
    await screen.findByText("Chưa xác minh được kết nối backend."),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Chỉ đường tài xế: Goong/)).not.toBeInTheDocument();
});

test("successful reset clears the plan and restores idle without another recommend", async () => {
  const client = createMockApiClient({
    recommend: vi.fn().mockResolvedValue(plan),
    reset: vi
      .fn()
      .mockResolvedValue({ reset: true, contract_version: "0.1.0" }),
  });
  mount(client);
  fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/ }));
  await screen.findByTestId("plan-hero");
  fireEvent.click(screen.getByRole("button", { name: "Đặt lại demo" }));
  expect(await screen.findByText(/Đã đặt lại tải phân bổ/)).toBeInTheDocument();
  expect(screen.queryByTestId("plan-hero")).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Chưa tìm trạm sạc" }),
  ).toBeInTheDocument();
  expect(client.reset).toHaveBeenCalledExactlyOnceWith({
    contract_version: "0.1.0",
  });
  expect(client.recommend).toHaveBeenCalledTimes(1);
});

test("failed reset preserves the plan and lets the user retry", async () => {
  const reset = vi
    .fn()
    .mockRejectedValueOnce(new ApiError(503, "unavailable", "down", null))
    .mockResolvedValueOnce({ reset: true, contract_version: "0.1.0" });
  mount(
    createMockApiClient({ recommend: vi.fn().mockResolvedValue(plan), reset }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/ }));
  await screen.findByTestId("plan-hero");
  fireEvent.click(screen.getByRole("button", { name: "Đặt lại demo" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Chưa đặt lại được demo",
  );
  expect(screen.getByTestId("plan-hero")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Đặt lại demo" }));
  await waitFor(() =>
    expect(screen.queryByTestId("plan-hero")).not.toBeInTheDocument(),
  );
  expect(reset).toHaveBeenCalledTimes(2);
});

test("unconfirmed reset never clears the current plan", async () => {
  mount(
    createMockApiClient({
      recommend: vi.fn().mockResolvedValue(plan),
      reset: vi
        .fn()
        .mockResolvedValue({ reset: false, contract_version: "0.1.0" }),
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/ }));
  await screen.findByTestId("plan-hero");
  fireEvent.click(screen.getByRole("button", { name: "Đặt lại demo" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Chưa đặt lại được demo",
  );
  expect(screen.getByTestId("plan-hero")).toBeInTheDocument();
});

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { AppRouter } from "../../app/router";
import { ApiProvider } from "../../app/ApiContext";
import { createMockApiClient } from "../../test/mockApiClient";
import { AsyncState } from "./AsyncState";
import { DataTypeBadge } from "./DataTypeBadge";

function renderApp(initial = "/") {
  const client = createMockApiClient();
  return render(
    <ApiProvider client={client}>
      <MemoryRouter initialEntries={[initial]}>
        <AppRouter />
      </MemoryRouter>
    </ApiProvider>,
  );
}

describe("routes and shared status UI", () => {
  test("defaults to driver route", () => {
    renderApp("/");
    expect(
      screen.getByRole("heading", { name: /Lên kế hoạch dừng sạc/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tài xế" })).toHaveClass(
      "nav-link--active",
    );
  });

  test("marks operator nav active", () => {
    renderApp("/operator");
    expect(screen.getByRole("link", { name: "Điều hành" })).toHaveClass(
      "nav-link--active",
    );
  });

  test("badge copy covers mock simulated real mixed", () => {
    const { rerender } = render(<DataTypeBadge dataType="mock" />);
    expect(screen.getByText("Dữ liệu mock")).toBeInTheDocument();
    rerender(<DataTypeBadge dataType="simulated" />);
    expect(screen.getByText("Dữ liệu mô phỏng")).toBeInTheDocument();
    rerender(<DataTypeBadge dataType="real" />);
    expect(screen.getByText("Dữ liệu thật")).toBeInTheDocument();
    rerender(<DataTypeBadge dataType="mixed" />);
    expect(screen.getByText("Dữ liệu hỗn hợp")).toBeInTheDocument();
  });

  test("async state exposes status role retry and empty copy", () => {
    const onRetry = vi.fn();
    const { rerender } = render(
      <AsyncState status="loading" loadingMessage="Loading plan…" />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Loading plan…");

    rerender(
      <AsyncState status="error" errorMessage="Failed" onRetry={onRetry} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(<AsyncState status="empty" emptyMessage="No feasible station." />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "No feasible station.",
    );
  });

  test("keeps children visible while loading when stale-while-refresh is on", () => {
    render(
      <AsyncState
        status="loading"
        loadingMessage="Refreshing pressure…"
        keepChildrenOnLoading
      >
        <p>Previous pressure layer</p>
      </AsyncState>,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Refreshing pressure…",
    );
    expect(screen.getByText("Previous pressure layer")).toBeInTheDocument();
  });
});

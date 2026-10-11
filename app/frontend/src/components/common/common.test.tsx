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
      screen.getByRole("heading", { name: /plan a charging stop/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Driver" })).toHaveClass(
      "nav-link--active",
    );
  });

  test("marks operator nav active", () => {
    renderApp("/operator");
    expect(screen.getByRole("link", { name: "Operator" })).toHaveClass(
      "nav-link--active",
    );
  });

  test("badge copy covers mock simulated real mixed", () => {
    const { rerender } = render(<DataTypeBadge dataType="mock" />);
    expect(screen.getByText("Mock data")).toBeInTheDocument();
    rerender(<DataTypeBadge dataType="simulated" />);
    expect(screen.getByText("Simulated data")).toBeInTheDocument();
    rerender(<DataTypeBadge dataType="real" />);
    expect(screen.getByText("Real data")).toBeInTheDocument();
    rerender(<DataTypeBadge dataType="mixed" />);
    expect(screen.getByText("Mixed data")).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(<AsyncState status="empty" emptyMessage="No feasible station." />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "No feasible station.",
    );
  });
});

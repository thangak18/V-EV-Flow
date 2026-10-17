import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import type { RuntimeContext } from "../../services/api";
import { DriverForm } from "./DriverForm";

function replayContext(observed_at: string | null): RuntimeContext {
  return {
    clock_mode: "replay",
    scenario: "normal",
    data_type: "simulated",
    observed_at,
    history_start: "2026-09-30T00:00:00+07:00",
    history_end: "2026-10-13T23:55:00+07:00",
    max_horizon_minutes: 180,
    places_available: false,
    available: true,
    message: "Historical fixture",
    allocation_backend: "memory",
  };
}

function renderForm(overrides: { pending?: boolean } = {}) {
  const onSubmit = vi.fn();
  render(
    <DriverForm pending={overrides.pending ?? false} onSubmit={onSubmit} />,
  );
  return { onSubmit };
}

describe("DriverForm", () => {
  test("live departures use click time while retaining the observed snapshot timestamp", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-13T16:02:10+07:00"));
    try {
      const onSubmit = vi.fn();
      render(
        <DriverForm
          pending={false}
          onSubmit={onSubmit}
          runtime={{
            clock_mode: "live",
            scenario: "normal",
            data_type: "real",
            observed_at: "2026-10-13T16:00:00+07:00",
            history_start: null,
            history_end: null,
            max_horizon_minutes: 180,
            places_available: false,
            available: true,
            message: "Live snapshot",
            allocation_backend: "sqlite",
          }}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/ }));
      expect(onSubmit).toHaveBeenCalledTimes(1);
      expect(onSubmit.mock.calls[0]![0]).toMatchObject({
        observed_at: "2026-10-13T16:00:00+07:00",
        depart_time: "2026-10-13T16:02:10.000+07:00",
      });
    } finally {
      vi.useRealTimers();
    }
  });

  test("uses independent endpoints and default vehicle values", () => {
    const { onSubmit } = renderForm();

    expect(screen.getByLabelText("Điểm đi")).toBeInTheDocument();
    expect(screen.getByLabelText(/SOC %/)).toHaveValue("20");
    expect(screen.getByLabelText(/Dung lượng pin/)).toHaveValue("60");
    expect(screen.getByLabelText(/Tiêu hao/)).toHaveValue("0.18");
    expect(screen.getByLabelText("Đầu cắm")).toHaveValue("CCS2");

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const request = onSubmit.mock.calls[0]![0];
    expect(request.origin).toEqual({ lat: 10.78, lng: 106.7 });
    expect(request.destination).toEqual({ lat: 10.35, lng: 107.08 });
    expect(request.vehicle.soc_pct).toBe(20);
    expect(request.vehicle.consumption_kwh_per_km).toBe(0.18);
    expect(request.request_id).toMatch(/^[0-9a-f-]{36}$/i);
  });

  test("keeps numeric fields empty after clear and blocks submit", () => {
    const { onSubmit } = renderForm();
    const soc = screen.getByLabelText(/SOC %/);
    const battery = screen.getByLabelText(/Dung lượng pin/);
    const consumption = screen.getByLabelText(/Tiêu hao/);

    fireEvent.change(soc, { target: { value: "" } });
    fireEvent.change(battery, { target: { value: "" } });
    fireEvent.change(consumption, { target: { value: "" } });

    expect(soc).toHaveValue("");
    expect(battery).toHaveValue("");
    expect(consumption).toHaveValue("");
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/Không để trống số/i);

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("allows retyping after clear without forcing a leading zero", () => {
    renderForm();
    const soc = screen.getByLabelText(/SOC %/);

    fireEvent.change(soc, { target: { value: "" } });
    expect(soc).toHaveValue("");

    fireEvent.change(soc, { target: { value: "3" } });
    expect(soc).toHaveValue("3");
    fireEvent.change(soc, { target: { value: "30" } });
    expect(soc).toHaveValue("30");
  });

  test("keeps trailing decimal separators while typing with dot or comma", () => {
    renderForm();
    const soc = screen.getByLabelText(/SOC %/);
    const consumption = screen.getByLabelText(/Tiêu hao/);

    fireEvent.change(soc, { target: { value: "30" } });
    fireEvent.change(soc, { target: { value: "30." } });
    expect(soc).toHaveValue("30.");
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();

    fireEvent.change(soc, { target: { value: "30.5" } });
    expect(soc).toHaveValue("30.5");

    fireEvent.change(consumption, { target: { value: "0," } });
    expect(consumption).toHaveValue("0,");
    fireEvent.change(consumption, { target: { value: "0,18" } });
    expect(consumption).toHaveValue("0,18");
  });

  test("normalizes comma decimals into API numbers on submit", () => {
    const { onSubmit } = renderForm();

    fireEvent.change(screen.getByLabelText(/SOC %/), {
      target: { value: "30,5" },
    });
    fireEvent.change(screen.getByLabelText(/Dung lượng pin/), {
      target: { value: "55" },
    });
    fireEvent.change(screen.getByLabelText(/Tiêu hao/), {
      target: { value: "0,18" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const vehicle = onSubmit.mock.calls[0]![0].vehicle;
    expect(vehicle.soc_pct).toBe(30.5);
    expect(vehicle.battery_kwh).toBe(55);
    expect(vehicle.consumption_kwh_per_km).toBe(0.18);
  });

  test("normalizes dot decimals into API numbers on submit", () => {
    const { onSubmit } = renderForm();

    fireEvent.change(screen.getByLabelText(/SOC %/), {
      target: { value: "40.25" },
    });
    fireEvent.change(screen.getByLabelText(/Tiêu hao/), {
      target: { value: "0.18" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0]![0].vehicle.soc_pct).toBe(40.25);
    expect(onSubmit.mock.calls[0]![0].vehicle.consumption_kwh_per_km).toBe(
      0.18,
    );
  });

  test("disables submit while pending and rejects invalid ranges", () => {
    const onSubmit = vi.fn();
    const { rerender } = render(
      <DriverForm pending={false} onSubmit={onSubmit} />,
    );
    fireEvent.change(screen.getByLabelText(/SOC %/), {
      target: { value: "120" },
    });
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();

    rerender(<DriverForm pending={true} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/SOC %/), {
      target: { value: "20" },
    });
    expect(screen.getByRole("button", { name: /Đang tìm/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Đang tìm/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test.each([null, "abc", "2026-10-13T16:00:00Z"])(
    "rejects invalid backend observation %s without asking the driver to edit it",
    (value) => {
      const onSubmit = vi.fn();
      const onRetryRuntime = vi.fn();
      render(
        <DriverForm
          pending={false}
          runtime={replayContext(value)}
          onSubmit={onSubmit}
          onRetryRuntime={onRetryRuntime}
        />,
      );
      expect(screen.queryByLabelText(/Giờ quan sát/i)).not.toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Tìm kế hoạch sạc/ }),
      ).toBeDisabled();
      expect(screen.getByRole("alert")).toHaveTextContent(
        /Chưa lấy được mốc dữ liệu trạm hợp lệ/,
      );
      fireEvent.click(screen.getByRole("button", { name: "Thử kết nối lại" }));
      expect(onRetryRuntime).toHaveBeenCalledTimes(1);
      expect(onSubmit).not.toHaveBeenCalled();
      expect(
        screen.getByText("Thông số xe").closest("details"),
      ).not.toHaveAttribute("open");
    },
  );

  test("shows a readonly data timestamp and submits the latest backend clock", () => {
    const onSubmit = vi.fn();
    const { rerender } = render(
      <DriverForm
        pending={false}
        runtime={replayContext("2026-10-13T16:00:00+07:00")}
        onSubmit={onSubmit}
      />,
    );
    expect(screen.queryByLabelText(/Giờ quan sát/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Dữ liệu lúc/)).toHaveTextContent("16:00");
    expect(screen.getByText(/Dữ liệu lúc/)).toHaveTextContent("13/10/2026");
    fireEvent.click(screen.getByRole("button", { name: "Tìm kế hoạch sạc" }));
    expect(onSubmit.mock.calls[0]![0]).toMatchObject({
      observed_at: "2026-10-13T16:00:00+07:00",
      depart_time: "2026-10-13T16:00:00+07:00",
    });
    rerender(
      <DriverForm
        pending={false}
        runtime={replayContext("2026-10-13T16:05:00+07:00")}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tìm kế hoạch sạc" }));
    expect(onSubmit.mock.calls[1]![0].observed_at).toBe(
      "2026-10-13T16:05:00+07:00",
    );
  });

  test("rejects battery and consumption of zero", () => {
    const { onSubmit } = renderForm();
    fireEvent.change(screen.getByLabelText(/Dung lượng pin/), {
      target: { value: "0" },
    });
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Dung lượng pin/), {
      target: { value: "60" },
    });
    fireEvent.change(screen.getByLabelText(/Tiêu hao/), {
      target: { value: "0" },
    });
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("keeps Advanced open when battery invalid even if user toggles summary", () => {
    renderForm();
    const details = document.querySelector(
      "details.driver-advanced",
    ) as HTMLDetailsElement;
    const summary = screen.getByText("Thông số xe");
    fireEvent.click(summary);
    expect(details).toHaveAttribute("open");

    fireEvent.change(screen.getByLabelText(/Dung lượng pin/), {
      target: { value: "" },
    });
    expect(details).toHaveClass("driver-advanced--locked");
    expect(details).toHaveAttribute("open");
    expect(screen.getByLabelText(/Dung lượng pin/)).toBeVisible();
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();

    // Simulate a collapse attempt while invalid (Playwright regression).
    details.open = false;
    details.dispatchEvent(new Event("toggle", { bubbles: true }));
    expect(details.open).toBe(true);
    expect(details).toHaveAttribute("open");
    expect(screen.getByLabelText(/Dung lượng pin/)).toBeVisible();
  });
});

test("an unfinished destination does not mark the valid origin as invalid", () => {
  render(<DriverForm pending={false} destination="" onSubmit={vi.fn()} />);
  expect(screen.getByLabelText("Điểm đi")).toHaveAttribute(
    "aria-invalid",
    "false",
  );
  expect(screen.getByLabelText("Điểm đến")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  expect(
    screen.getByRole("button", { name: /Tìm kế hoạch sạc/ }),
  ).toBeDisabled();
});

test("replay departure selects an actual snapshot and resets explicitly", () => {
  const onSubmit = vi.fn(),
    onDepartureChange = vi.fn();
  render(
    <DriverForm
      pending={false}
      runtime={replayContext("2026-10-13T16:00:00+07:00")}
      onSubmit={onSubmit}
      onDepartureChange={onDepartureChange}
    />,
  );
  const departure = screen.getByLabelText("Giờ khởi hành");
  expect(departure).toHaveValue("2026-10-13T16:00");
  fireEvent.change(departure, { target: { value: "2026-10-13T16:30" } });
  fireEvent.click(screen.getByRole("button", { name: "Tìm kế hoạch sạc" }));
  expect(onSubmit.mock.calls[0]?.[0]).toMatchObject({
    observed_at: "2026-10-13T16:30:00+07:00",
    depart_time: "2026-10-13T16:30:00+07:00",
  });
  expect(onDepartureChange).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Dùng mốc dữ liệu" }));
  expect(departure).toHaveValue("2026-10-13T16:00");
});

test.each(["", "2026-09-29T23:59", "2026-10-14T00:00", "2026-10-17T16:00"])(
  "blocks unavailable departure %s without changing the snapshot",
  (value) => {
    const onSubmit = vi.fn();
    render(
      <DriverForm
        pending={false}
        runtime={replayContext("2026-10-13T16:00:00+07:00")}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText("Giờ khởi hành"), {
      target: { value },
    });
    expect(
      screen.getByRole("button", { name: "Tìm kế hoạch sạc" }),
    ).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/khởi hành/);
    expect(screen.getByText(/Dữ liệu lúc/)).toHaveTextContent("16:00");
    expect(onSubmit).not.toHaveBeenCalled();
  },
);

test("switching demand scenario resets departure to that scenario's data clock", () => {
  render(
    <DriverForm
      pending={false}
      runtime={replayContext("2026-10-13T16:00:00+07:00")}
      onSubmit={vi.fn()}
    />,
  );
  fireEvent.change(screen.getByLabelText("Giờ khởi hành"), {
    target: { value: "2026-10-13T16:30" },
  });
  fireEvent.change(screen.getByLabelText("Kịch bản nhu cầu sạc"), {
    target: { value: "tet" },
  });
  expect(screen.getByLabelText("Giờ khởi hành")).toHaveValue(
    "2026-10-13T16:00",
  );
});

test.each([
  "2026-10-13T08:00",
  "2026-10-13T19:00",
  "2026-10-13T20:00",
  "2026-10-13T20:02",
])(
  "replays %s from history without a three-hour departure restriction",
  (value) => {
    const onSubmit = vi.fn();
    render(
      <DriverForm
        pending={false}
        runtime={replayContext("2026-10-13T16:00:00+07:00")}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText("Giờ khởi hành"), {
      target: { value },
    });
    expect(
      screen.getByRole("button", { name: "Tìm kế hoạch sạc" }),
    ).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Tìm kế hoạch sạc" }));
    const request = onSubmit.mock.calls[0]?.[0];
    expect(request.depart_time).toBe(`${value}:00+07:00`);
    const expected = value.endsWith("20:02")
      ? "2026-10-13T20:00:00+07:00"
      : `${value}:00+07:00`;
    expect(request.observed_at).toBe(expected);
    expect(
      screen.getByText(/Dữ liệu lúc/).querySelector("time"),
    ).toHaveAttribute("datetime", expected);
  },
);

test("live planned departure keeps the latest real observation", () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-13T16:02:00+07:00"));
  try {
    const onSubmit = vi.fn();
    render(
      <DriverForm
        pending={false}
        runtime={{
          ...replayContext("2026-10-13T16:00:00+07:00"),
          clock_mode: "live",
          data_type: "real",
        }}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText("Giờ khởi hành"), {
      target: { value: "2026-10-13T16:30" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tìm kế hoạch sạc" }));
    expect(onSubmit.mock.calls[0]?.[0]).toMatchObject({
      observed_at: "2026-10-13T16:00:00+07:00",
      depart_time: "2026-10-13T16:30:00+07:00",
    });
  } finally {
    vi.useRealTimers();
  }
});

test("replay departure picker reaches 24 hours past the default snapshot", () => {
  render(
    <DriverForm
      pending={false}
      runtime={{
        ...replayContext("2026-10-17T12:25:00+07:00"),
        history_end: "2026-10-18T23:55:00+07:00",
      }}
      onSubmit={vi.fn()}
    />,
  );
  const picker = screen.getByLabelText("Giờ khởi hành");
  expect(picker).toHaveAttribute("max", "2026-10-18T12:25");
  fireEvent.change(picker, { target: { value: "2026-10-18T12:25" } });
  expect(
    screen.getByRole("button", { name: "Tìm kế hoạch sạc" }),
  ).toBeEnabled();
  fireEvent.change(picker, { target: { value: "2026-10-18T12:30" } });
  expect(
    screen.getByRole("button", { name: "Tìm kế hoạch sạc" }),
  ).toBeDisabled();
});

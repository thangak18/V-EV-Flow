import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { DriverForm } from "./DriverForm";

function renderForm(overrides: { pending?: boolean } = {}) {
  const onSubmit = vi.fn();
  const onPresetChange = vi.fn();
  render(
    <DriverForm
      pending={overrides.pending ?? false}
      presetId="hcm_vt"
      onPresetChange={onPresetChange}
      onSubmit={onSubmit}
    />,
  );
  return { onSubmit, onPresetChange };
}

describe("DriverForm", () => {
  test("uses corridor presets and default vehicle values", () => {
    const { onSubmit } = renderForm();

    expect(screen.getByDisplayValue("TP.HCM → Vũng Tàu")).toBeInTheDocument();
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
    const onPresetChange = vi.fn();
    const { rerender } = render(
      <DriverForm
        pending={false}
        presetId="hcm_vt"
        onPresetChange={onPresetChange}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText(/SOC %/), {
      target: { value: "120" },
    });
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();

    rerender(
      <DriverForm
        pending={true}
        presetId="hcm_vt"
        onPresetChange={onPresetChange}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText(/SOC %/), {
      target: { value: "20" },
    });
    expect(screen.getByRole("button", { name: /Đang tìm/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Đang tìm/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("rejects demo time without timezone", () => {
    const { onSubmit } = renderForm();
    fireEvent.change(screen.getByLabelText(/Giờ demo/i), {
      target: { value: "abc" },
    });
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/múi giờ/i);
    expect(onSubmit).not.toHaveBeenCalled();
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

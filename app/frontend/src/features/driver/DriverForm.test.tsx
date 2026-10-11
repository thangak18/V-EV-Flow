import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { DriverForm } from "./DriverForm";

describe("DriverForm", () => {
  test("uses corridor presets and default vehicle values", () => {
    const onSubmit = vi.fn();
    const onPresetChange = vi.fn();
    render(
      <DriverForm
        pending={false}
        presetId="hcm_vt"
        onPresetChange={onPresetChange}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByDisplayValue("TP.HCM → Vũng Tàu")).toBeInTheDocument();
    expect(screen.getByLabelText("SOC %")).toHaveValue(20);
    expect(screen.getByLabelText("Battery kWh")).toHaveValue(60);
    expect(screen.getByLabelText("Consumption kWh/km")).toHaveValue(0.18);
    expect(screen.getByLabelText("Connector")).toHaveValue("CCS2");

    fireEvent.click(screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const request = onSubmit.mock.calls[0]![0];
    expect(request.origin).toEqual({ lat: 10.78, lng: 106.7 });
    expect(request.destination).toEqual({ lat: 10.35, lng: 107.08 });
    expect(request.vehicle.soc_pct).toBe(20);
    expect(request.request_id).toMatch(/^[0-9a-f-]{36}$/i);
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
    fireEvent.change(screen.getByLabelText("SOC %"), {
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
    fireEvent.change(screen.getByLabelText("SOC %"), {
      target: { value: "20" },
    });
    expect(
      screen.getByRole("button", { name: /Finding plan/i }),
    ).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Finding plan/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("rejects demo time without timezone", () => {
    const onSubmit = vi.fn();
    render(
      <DriverForm
        pending={false}
        presetId="hcm_vt"
        onPresetChange={vi.fn()}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Demo time/i), {
      target: { value: "abc" },
    });
    expect(
      screen.getByRole("button", { name: /Tìm kế hoạch sạc/i }),
    ).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/timezone/i);
  });
});

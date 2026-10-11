import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { SimulationControls } from "./SimulationControls";

function renderControls() {
  const onSeedChange = vi.fn();
  const onVehicleCountChange = vi.fn();
  const onRun = vi.fn();
  render(
    <SimulationControls
      seed={42}
      vehicleCount={100}
      onSeedChange={onSeedChange}
      onVehicleCountChange={onVehicleCountChange}
      onRun={onRun}
      pending={false}
    />,
  );
  return {
    onSeedChange,
    onVehicleCountChange,
    onRun,
    seed: screen.getByLabelText("Seed"),
    vehicles: screen.getByLabelText("Vehicles"),
    submit: screen.getByRole("button", { name: /Compare 3 strategies/i }),
  };
}

/** Simulate typing one character at a time through the controlled onChange filter. */
function typeSequentially(input: HTMLElement, text: string, currentValue = "") {
  let value = currentValue;
  for (const char of text) {
    value += char;
    fireEvent.change(input, { target: { value } });
  }
}

describe("SimulationControls", () => {
  test("keeps empty seed/vehicles drafts and does not coerce empty to 0", () => {
    const {
      onSeedChange,
      onVehicleCountChange,
      onRun,
      seed,
      vehicles,
      submit,
    } = renderControls();

    fireEvent.change(seed, { target: { value: "" } });
    fireEvent.change(vehicles, { target: { value: "" } });
    expect(seed).toHaveValue("");
    expect(vehicles).toHaveValue("");
    expect(submit).toBeDisabled();
    expect(screen.getByText("Seed phải là số nguyên")).toBeInTheDocument();
    expect(
      screen.getByText("Số xe phải là số nguyên lớn hơn hoặc bằng 1"),
    ).toBeInTheDocument();
    expect(onSeedChange).not.toHaveBeenCalled();
    expect(onVehicleCountChange).not.toHaveBeenCalled();
    expect(onRun).not.toHaveBeenCalled();

    fireEvent.change(seed, { target: { value: "0" } });
    fireEvent.change(vehicles, { target: { value: "50" } });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    expect(onSeedChange).toHaveBeenCalledWith(0);
    expect(onVehicleCountChange).toHaveBeenCalledWith(50);
    expect(onRun).toHaveBeenCalledWith(0, 50);
  });

  test("typing 1.5 / 1,5 keeps separators and blocks until integer", () => {
    const { onRun, seed, vehicles, submit } = renderControls();

    fireEvent.change(seed, { target: { value: "" } });
    typeSequentially(seed, "1.5");
    expect(seed).toHaveValue("1.5");
    expect(screen.getByText("Seed phải là số nguyên")).toBeInTheDocument();
    expect(submit).toBeDisabled();

    fireEvent.change(vehicles, { target: { value: "" } });
    typeSequentially(vehicles, "1,5");
    expect(vehicles).toHaveValue("1,5");
    expect(
      screen.getByText("Số xe phải là số nguyên lớn hơn hoặc bằng 1"),
    ).toBeInTheDocument();
    expect(submit).toBeDisabled();
    expect(onRun).not.toHaveBeenCalled();

    fireEvent.change(seed, { target: { value: "15" } });
    fireEvent.change(vehicles, { target: { value: "15" } });
    expect(seed).toHaveValue("15");
    expect(vehicles).toHaveValue("15");
    expect(
      screen.queryByText("Seed phải là số nguyên"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Số xe phải là số nguyên lớn hơn hoặc bằng 1"),
    ).not.toBeInTheDocument();
    expect(submit).toBeEnabled();
  });

  test("paste of decimal drafts stays visible and does not submit", () => {
    const { onRun, seed, vehicles, submit } = renderControls();

    fireEvent.change(seed, { target: { value: "1.5" } });
    fireEvent.change(vehicles, { target: { value: "1,5" } });
    expect(seed).toHaveValue("1.5");
    expect(vehicles).toHaveValue("1,5");
    expect(submit).toBeDisabled();
    fireEvent.click(submit);
    expect(onRun).not.toHaveBeenCalled();
  });
});

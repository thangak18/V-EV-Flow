import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { SimulationControls } from "./SimulationControls";

describe("SimulationControls", () => {
  test("keeps empty seed/vehicles drafts and does not coerce empty to 0", () => {
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

    const seed = screen.getByLabelText("Seed");
    const vehicles = screen.getByLabelText("Vehicles");
    const submit = screen.getByRole("button", {
      name: /Compare 3 strategies/i,
    });

    fireEvent.change(seed, { target: { value: "" } });
    fireEvent.change(vehicles, { target: { value: "" } });
    expect(seed).toHaveValue("");
    expect(vehicles).toHaveValue("");
    expect(submit).toBeDisabled();
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
});

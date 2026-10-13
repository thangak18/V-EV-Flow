import { useState, type FormEvent } from "react";

import { isNumericDraft, parseInteger } from "../driver/numberField";

type Props = {
  seed: number;
  vehicleCount: number;
  onSeedChange: (seed: number) => void;
  onVehicleCountChange: (count: number) => void;
  onRun: (seed: number, vehicleCount: number) => void;
  pending: boolean;
};

function seedErrorMessage(draft: string): string | null {
  if (parseInteger(draft) !== null) return null;
  return "Seed phải là số nguyên";
}

function vehiclesErrorMessage(draft: string): string | null {
  const parsed = parseInteger(draft);
  if (parsed !== null && parsed >= 1) return null;
  return "Số xe phải là số nguyên lớn hơn hoặc bằng 1";
}

export function SimulationControls({
  seed,
  vehicleCount,
  onSeedChange,
  onVehicleCountChange,
  onRun,
  pending,
}: Props) {
  const [seedDraft, setSeedDraft] = useState(() => String(seed));
  const [vehiclesDraft, setVehiclesDraft] = useState(() =>
    String(vehicleCount),
  );

  const parsedSeed = parseInteger(seedDraft);
  const parsedVehicles = parseInteger(vehiclesDraft);
  const seedError = seedErrorMessage(seedDraft);
  const vehiclesError = vehiclesErrorMessage(vehiclesDraft);
  const invalid = seedError !== null || vehiclesError !== null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending || parsedSeed === null || parsedVehicles === null) return;
    if (parsedVehicles < 1) return;
    onSeedChange(parsedSeed);
    onVehicleCountChange(parsedVehicles);
    onRun(parsedSeed, parsedVehicles);
  }

  return (
    <form className="simulation-controls" onSubmit={handleSubmit}>
      <div className="simulation-field">
        <label htmlFor="sim-seed">Seed (mầm ngẫu nhiên)</label>
        <input
          id="sim-seed"
          type="text"
          inputMode="numeric"
          value={seedDraft}
          onChange={(event) => {
            const next = event.target.value;
            // Keep decimal drafts visible (e.g. "1.5") — validate as integer separately.
            if (isNumericDraft(next)) setSeedDraft(next);
          }}
          aria-invalid={seedError !== null}
          aria-describedby={seedError ? "sim-seed-error" : undefined}
          autoComplete="off"
        />
        {seedError ? (
          <p id="sim-seed-error" className="field-error" role="alert">
            {seedError}
          </p>
        ) : null}
      </div>
      <div className="simulation-field">
        <label htmlFor="sim-vehicles">Số xe</label>
        <input
          id="sim-vehicles"
          type="text"
          inputMode="numeric"
          value={vehiclesDraft}
          onChange={(event) => {
            const next = event.target.value;
            if (isNumericDraft(next)) setVehiclesDraft(next);
          }}
          aria-invalid={vehiclesError !== null}
          aria-describedby={vehiclesError ? "sim-vehicles-error" : undefined}
          autoComplete="off"
        />
        {vehiclesError ? (
          <p id="sim-vehicles-error" className="field-error" role="alert">
            {vehiclesError}
          </p>
        ) : null}
      </div>
      <button type="submit" disabled={pending || invalid}>
        {pending ? "Đang chạy…" : "So sánh 3 chiến lược"}
      </button>
    </form>
  );
}

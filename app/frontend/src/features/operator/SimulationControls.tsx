import { useState, type FormEvent } from "react";

import { isIntegerDraft, parseInteger } from "../driver/numberField";

type Props = {
  seed: number;
  vehicleCount: number;
  onSeedChange: (seed: number) => void;
  onVehicleCountChange: (count: number) => void;
  onRun: (seed: number, vehicleCount: number) => void;
  pending: boolean;
};

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
  const seedInvalid = parsedSeed === null;
  const vehiclesInvalid = parsedVehicles === null || parsedVehicles < 1;
  const invalid = seedInvalid || vehiclesInvalid;

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
      <label>
        Seed
        <input
          type="text"
          inputMode="numeric"
          value={seedDraft}
          onChange={(event) => {
            const next = event.target.value;
            if (isIntegerDraft(next)) setSeedDraft(next);
          }}
          aria-invalid={seedInvalid}
          autoComplete="off"
        />
      </label>
      <label>
        Vehicles
        <input
          type="text"
          inputMode="numeric"
          value={vehiclesDraft}
          onChange={(event) => {
            const next = event.target.value;
            if (isIntegerDraft(next)) setVehiclesDraft(next);
          }}
          aria-invalid={vehiclesInvalid}
          autoComplete="off"
        />
      </label>
      {invalid ? (
        <p className="field-error" role="alert">
          Enter an integer seed (0 allowed) and vehicles ≥ 1. Empty fields are
          not submitted.
        </p>
      ) : null}
      <button type="submit" disabled={pending || invalid}>
        {pending ? "Running…" : "Compare 3 strategies"}
      </button>
    </form>
  );
}

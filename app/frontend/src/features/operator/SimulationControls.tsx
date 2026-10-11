type Props = {
  seed: number;
  vehicleCount: number;
  onSeedChange: (seed: number) => void;
  onVehicleCountChange: (count: number) => void;
  onRun: () => void;
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
  const invalid =
    !Number.isFinite(seed) ||
    !Number.isInteger(seed) ||
    !Number.isFinite(vehicleCount) ||
    !Number.isInteger(vehicleCount) ||
    vehicleCount < 1;

  return (
    <form
      className="simulation-controls"
      onSubmit={(event) => {
        event.preventDefault();
        if (!pending && !invalid) onRun();
      }}
    >
      <label>
        Seed
        <input
          type="number"
          value={seed}
          onChange={(event) => onSeedChange(Number(event.target.value))}
          aria-invalid={!Number.isInteger(seed)}
        />
      </label>
      <label>
        Vehicles
        <input
          type="number"
          min={1}
          value={vehicleCount}
          onChange={(event) => onVehicleCountChange(Number(event.target.value))}
          aria-invalid={vehicleCount < 1}
        />
      </label>
      {invalid ? (
        <p className="field-error" role="alert">
          Seed must be an integer and vehicles must be ≥ 1.
        </p>
      ) : null}
      <button type="submit" disabled={pending || invalid}>
        {pending ? "Running…" : "Compare 3 strategies"}
      </button>
    </form>
  );
}

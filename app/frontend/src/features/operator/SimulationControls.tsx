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
  return (
    <form
      className="simulation-controls"
      onSubmit={(event) => {
        event.preventDefault();
        if (!pending) onRun();
      }}
    >
      <label>
        Seed
        <input
          type="number"
          value={seed}
          onChange={(event) => onSeedChange(Number(event.target.value))}
        />
      </label>
      <label>
        Vehicles
        <input
          type="number"
          min={1}
          value={vehicleCount}
          onChange={(event) => onVehicleCountChange(Number(event.target.value))}
        />
      </label>
      <button type="submit" disabled={pending}>
        {pending ? "Running…" : "Compare 3 strategies"}
      </button>
    </form>
  );
}

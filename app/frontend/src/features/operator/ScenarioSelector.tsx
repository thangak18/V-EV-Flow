import type { Scenario } from "../../services/api";

type Props = {
  scenario: Scenario;
  time: string;
  onScenarioChange: (scenario: Scenario) => void;
  onTimeChange: (time: string) => void;
  onApply: () => void;
  pending?: boolean;
};

export function ScenarioSelector({
  scenario,
  time,
  onScenarioChange,
  onTimeChange,
  onApply,
  pending = false,
}: Props) {
  return (
    <form
      className="scenario-selector"
      onSubmit={(event) => {
        event.preventDefault();
        onApply();
      }}
    >
      <label>
        Scenario
        <select
          value={scenario}
          onChange={(event) => onScenarioChange(event.target.value as Scenario)}
        >
          <option value="normal">Normal day</option>
          <option value="holiday_30_4">30/4 holiday</option>
          <option value="tet">Tết</option>
        </select>
      </label>
      <label>
        Time (+07:00)
        <input
          type="text"
          value={time}
          onChange={(event) => onTimeChange(event.target.value)}
        />
      </label>
      <button type="submit" disabled={pending}>
        {pending ? "Loading pressure…" : "Apply scenario"}
      </button>
    </form>
  );
}

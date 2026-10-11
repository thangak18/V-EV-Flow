import { isTimezoneAwareIso } from "../../services/errors";
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
  const timeInvalid = !isTimezoneAwareIso(time);

  return (
    <form
      className="scenario-selector"
      onSubmit={(event) => {
        event.preventDefault();
        if (!pending && !timeInvalid) onApply();
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
          className="input-datetime"
          type="text"
          value={time}
          onChange={(event) => onTimeChange(event.target.value)}
          aria-invalid={timeInvalid}
          autoComplete="off"
          spellCheck={false}
        />
      </label>
      {timeInvalid ? (
        <p className="field-error" role="alert">
          Time must be ISO-8601 with timezone (e.g. 2026-10-13T16:00:00+07:00).
        </p>
      ) : null}
      <button type="submit" disabled={pending || timeInvalid}>
        {pending ? "Loading pressure…" : "Apply scenario"}
      </button>
    </form>
  );
}

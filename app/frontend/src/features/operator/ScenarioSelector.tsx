import { isPlus07FiveMinuteBucket } from "../../services/errors";
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
  const timeInvalid = !isPlus07FiveMinuteBucket(time);

  return (
    <form
      className="scenario-selector toolbar-card"
      onSubmit={(event) => {
        event.preventDefault();
        if (!pending && !timeInvalid) onApply();
      }}
    >
      <label className="field-chip">
        <span className="field-chip__label">Kịch bản</span>
        <select
          value={scenario}
          onChange={(event) => onScenarioChange(event.target.value as Scenario)}
        >
          <option value="normal">Ngày thường</option>
          <option value="holiday_30_4">Lễ 30/4</option>
          <option value="tet">Tết</option>
        </select>
      </label>
      <label className="field-chip">
        <span className="field-chip__label">Thời điểm (+07:00)</span>
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
          Thời điểm phải là +07:00, căn 5 phút (ví dụ
          2026-10-13T16:00:00+07:00).
        </p>
      ) : null}
      <button
        type="submit"
        className="btn-primary"
        disabled={pending || timeInvalid}
      >
        {pending ? "Đang tải áp lực…" : "Áp dụng kịch bản"}
      </button>
    </form>
  );
}

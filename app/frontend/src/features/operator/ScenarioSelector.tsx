import { isPlus07FiveMinuteBucket } from "../../services/errors";
import type { Scenario } from "../../services/api";

type Props = {
  scenario: Scenario;
  time: string;
  systemTime?: string;
  onScenarioChange: (scenario: Scenario) => void;
  onTimeChange: (time: string) => void;
  onApply: () => void;
  pending?: boolean;
};

export function ScenarioSelector({
  scenario,
  time,
  systemTime = time,
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
      <div className="operator-data-clock">
        <span>
          {time === systemTime ? "Dữ liệu lúc" : "Đang xem lịch sử lúc"}
        </span>
        {timeInvalid ? (
          <strong>Chưa có mốc dữ liệu hợp lệ</strong>
        ) : (
          <time dateTime={time}>
            {new Date(time).toLocaleString("vi-VN", {
              timeZone: "Asia/Ho_Chi_Minh",
              hour: "2-digit",
              minute: "2-digit",
              day: "2-digit",
              month: "2-digit",
              year: "numeric",
            })}
          </time>
        )}
        <small>
          Giờ Việt Nam ·{" "}
          {time === systemTime
            ? "Tự động lấy từ hệ thống"
            : "Mốc lịch sử được chọn thủ công"}
        </small>
      </div>
      <button
        type="submit"
        className="btn-primary"
        disabled={pending || timeInvalid}
      >
        {pending ? "Đang tải áp lực…" : "Áp dụng kịch bản"}
      </button>
      <details className="operator-time-settings">
        <summary>Thiết lập nâng cao</summary>
        <p>
          Chọn mốc lịch sử khi cần xem lại dự báo. Giờ được tính theo giờ Việt
          Nam, mỗi mốc cách nhau 5 phút.
        </p>
        <label className="field-chip">
          <span className="field-chip__label">Xem dữ liệu tại</span>
          <input
            type="datetime-local"
            step={300}
            value={time.slice(0, 16)}
            onChange={(event) =>
              onTimeChange(
                event.target.value
                  ? `${event.target.value.slice(0, 16)}:00+07:00`
                  : "",
              )
            }
            aria-invalid={timeInvalid}
          />
        </label>
        <button
          type="button"
          className="btn-secondary"
          disabled={
            !isPlus07FiveMinuteBucket(systemTime) || time === systemTime
          }
          onClick={() => onTimeChange(systemTime)}
        >
          Dùng mốc hệ thống
        </button>
      </details>
      {timeInvalid && !pending ? (
        <p className="field-error" role="alert">
          Chọn ngày giờ hợp lệ theo mốc 5 phút trong Thiết lập nâng cao, hoặc
          dùng lại mốc hệ thống.
        </p>
      ) : null}
    </form>
  );
}

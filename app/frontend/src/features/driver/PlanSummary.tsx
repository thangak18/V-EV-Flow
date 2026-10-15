import type { RecommendationResult } from "../../services/api";

import { displayDistance, displayReason } from "./presentation";

type Props = {
  result: RecommendationResult;
  stationNames?: Record<string, string>;
  onFocusMap?: () => void;
};

function formatPct(value: number): string {
  if (value > 0 && value < 0.01) return "<1%";
  if (value > 0.99 && value < 1) return ">99%";
  return `${Math.round(value * 100)}%`;
}

const HCMC_TZ = "Asia/Ho_Chi_Minh";

/** Format ETA in Vietnam time so the (+07:00) label matches the clock. */
export function formatEtaTime(value: string): string {
  return new Date(value).toLocaleString("vi-VN", {
    timeZone: HCMC_TZ,
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  });
}

export function PlanSummary({ result, stationNames = {}, onFocusMap }: Props) {
  const hasPlan = result.primary != null || result.backup != null;
  const primary = result.primary;
  const primaryName = primary
    ? (stationNames[primary.station_id] ?? primary.station_id)
    : null;
  const backup = result.backup;
  const backupName = backup
    ? (stationNames[backup.station_id] ?? backup.station_id)
    : null;

  return (
    <section
      className="plan-summary plan-summary--hero"
      aria-labelledby="plan-summary-title"
    >
      <p className="eyebrow">Kế hoạch sạc</p>
      <h2 id="plan-summary-title" className="visually-hidden">
        Trạm đề xuất
      </h2>

      {!hasPlan ? (
        <p className="status-message" role="status">
          Không có trạm khả thi cho chuyến này.
        </p>
      ) : (
        <>
          {primary ? (
            <div className="plan-hero" data-testid="plan-hero">
              <p className="plan-hero__label">Trạm chính</p>
              <h3 className="plan-hero__name">{primaryName}</h3>
              <div className="plan-kpi-row">
                <div className="plan-kpi">
                  <strong data-probability={primary.p_available}>
                    {formatPct(primary.p_available)}
                  </strong>
                  <span>Khả năng có cổng</span>
                </div>
                <div className="plan-kpi">
                  <strong>{formatEtaTime(primary.eta)}</strong>
                  <span>Đến lúc (+07:00)</span>
                </div>
              </div>
              <div
                className="plan-kpi-bar"
                style={{ width: `${primary.p_available * 100}%` }}
                aria-hidden
              />
              <dl className="plan-hero__metrics">
                <div>
                  <dd>{displayDistance(primary.distance_km)} km</dd>
                  <dt>Khoảng cách</dt>
                </div>
                <div>
                  <dd>
                    {primary.arrival_soc_pct.toFixed(1).replace(".", ",")}%
                  </dd>
                  <dt>Pin khi đến</dt>
                </div>
                <div>
                  <dd>+{displayDistance(primary.detour_km)} km</dd>
                  <dt>Đường vòng</dt>
                </div>
              </dl>
              {result.plan_p != null ? (
                <p className="plan-confidence">
                  Ước lượng kế hoạch {formatPct(result.plan_p)}
                  {result.plan_p_assumption ? (
                    <span className="plan-confidence__hint">
                      {" "}
                      · giả định{" "}
                      {result.plan_p_assumption === "independent_stations"
                        ? "hai trạm độc lập"
                        : result.plan_p_assumption}
                    </span>
                  ) : null}
                </p>
              ) : null}
              <button
                type="button"
                className="btn-primary plan-hero__cta"
                onClick={onFocusMap}
              >
                Xem trạm trên bản đồ
              </button>
            </div>
          ) : null}

          {backup ? (
            <article className="plan-backup">
              <p className="plan-hero__label">Trạm dự phòng</p>
              <h3>{backupName}</h3>
              <dl className="plan-backup__metrics">
                <div>
                  <dt>Khả năng có cổng</dt>
                  <dd data-probability={backup.p_available}>
                    {formatPct(backup.p_available)}
                  </dd>
                </div>
                <div>
                  <dt>Đến lúc</dt>
                  <dd>{formatEtaTime(backup.eta)}</dd>
                </div>
              </dl>
            </article>
          ) : (
            <p className="status-message">Không có trạm dự phòng.</p>
          )}
        </>
      )}

      {result.reasons.length > 0 ? (
        <ul className="reason-list">
          {result.reasons.map((reason) => (
            <li key={reason}>{displayReason(reason)}</li>
          ))}
        </ul>
      ) : null}

      <details className="tech-details">
        <summary>Chi tiết kỹ thuật</summary>
        <div className="tech-details__body">
          {result.plan_p != null && result.plan_p_assumption ? (
            <p>Giả định ước lượng: {result.plan_p_assumption}</p>
          ) : null}
          <p>Phiên bản mô hình: {result.model_version}</p>
          <p>Cách phân bổ: {result.allocation_method}</p>
          {primary ? <p>Mã trạm chính: {primary.station_id}</p> : null}
          {backup ? <p>Mã trạm dự phòng: {backup.station_id}</p> : null}
        </div>
      </details>
    </section>
  );
}

export function PlanEmptyState() {
  return (
    <section className="plan-empty" aria-labelledby="plan-empty-title">
      <p className="eyebrow">Kế hoạch sạc</p>
      <h2 id="plan-empty-title">Chưa tìm trạm sạc</h2>
      <div className="plan-empty__icon" aria-hidden>
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
          <rect
            x="8"
            y="12"
            width="40"
            height="32"
            rx="6"
            stroke="currentColor"
            strokeWidth="2.5"
          />
          <circle
            cx="28"
            cy="28"
            r="8"
            stroke="currentColor"
            strokeWidth="2.5"
          />
          <path
            d="M33 33 40 40"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <p className="plan-empty__copy">
        Kiểm tra hành trình, pin hiện tại và đầu cắm, rồi bấm tìm kế hoạch sạc.
      </p>
      <p className="plan-empty__hint">Kết quả sẽ hiện tại đây.</p>
    </section>
  );
}

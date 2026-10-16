import type { RecommendationResult } from "../../services/api";

import { ModelExplanation } from "./ModelExplanation";

import { displayDistance, displayReason } from "./presentation";

type Props = {
  result: RecommendationResult;
  stationNames?: Record<string, string>;
  onFocusMap?: (role: "primary" | "backup") => void;
  canFocusPrimary?: boolean;
  canFocusBackup?: boolean;
};

function formatPct(value: number): string {
  if (value > 0 && value < 0.01) return "<1%";
  if (value > 0.99 && value < 1) return ">99%";
  return `${Math.round(value * 100)}%`;
}

const HCMC_TZ = "Asia/Ho_Chi_Minh";

/** Format ETA in Vietnam time so the (+07:00) label matches the clock. */
export function formatEtaTime(value: string): string {
  const date = new Date(value);
  const clock = date.toLocaleTimeString("vi-VN", {
    timeZone: HCMC_TZ,
    hour: "2-digit",
    minute: "2-digit",
  });
  const day = date.toLocaleDateString("vi-VN", {
    timeZone: HCMC_TZ,
    day: "2-digit",
    month: "2-digit",
  });
  return `${clock} · ${day}`;
}

export function PlanSummary({
  result,
  stationNames = {},
  onFocusMap,
  canFocusPrimary = true,
  canFocusBackup = true,
}: Props) {
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
                  <dt>Từ điểm xuất phát</dt>
                </div>
                <div>
                  <dd>
                    {primary.arrival_soc_pct.toFixed(1).replace(".", ",")}%
                  </dd>
                  <dt>Pin khi đến</dt>
                </div>
                <div>
                  <dd>+{displayDistance(primary.detour_km)} km</dd>
                  <dt>Đi thêm để ghé trạm</dt>
                </div>
              </dl>
              {result.plan_p != null ? (
                <p className="plan-confidence">
                  Khả năng kế hoạch có chỗ: {formatPct(result.plan_p)}
                </p>
              ) : null}
              <button
                type="button"
                className="btn-primary plan-hero__cta"
                onClick={() => onFocusMap?.("primary")}
                disabled={!canFocusPrimary}
                title={
                  !canFocusPrimary
                    ? "Trạm chưa có tọa độ để định vị"
                    : undefined
                }
              >
                Định vị trạm chính
              </button>
            </div>
          ) : null}

          {backup ? (
            <article className="plan-backup">
              <p className="plan-hero__label">Trạm dự phòng</p>
              <span className="backup-step">PHƯƠNG ÁN B</span>
              <h3>{backupName}</h3>
              <p className="backup-explainer">
                Nếu trạm chính không còn chỗ, bạn có thể tiếp tục tới trạm này.
                Thời gian và pin bên dưới đã tính cho hành trình qua trạm chính.
              </p>
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
                <div>
                  <dt>Pin khi tới trạm dự phòng</dt>
                  <dd>{backup.arrival_soc_pct.toFixed(1)}%</dd>
                </div>
                <div>
                  <dt>Tổng quãng đường tới dự phòng</dt>
                  <dd>{displayDistance(backup.distance_km)} km</dd>
                </div>
              </dl>
              <p className="metric-note">
                Xác suất còn cổng tại giờ đến dự kiến; chưa phải xác nhận giữ
                chỗ.
              </p>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => onFocusMap?.("backup")}
                disabled={!canFocusBackup}
                title={
                  !canFocusBackup ? "Trạm chưa có tọa độ để định vị" : undefined
                }
              >
                Định vị trạm dự phòng
              </button>
            </article>
          ) : (
            <p className="status-message">Không có trạm dự phòng.</p>
          )}

          {primary?.explanation ? (
            <ModelExplanation explanation={primary.explanation} />
          ) : null}
          {result.time_shift_evaluated && !result.time_shift_estimate ? (
            <p className="status-message" data-testid="time-shift-none">
              Giữ giờ khởi hành hiện tại — chưa có gợi ý đổi giờ phù hợp.
            </p>
          ) : null}
          {result.time_shift_estimate ? (
            <aside
              className="time-shift-card"
              data-testid="time-shift-suggestion"
            >
              <h3>Gợi ý khởi hành lệch giờ</h3>
              <p>
                Khởi hành muộn {result.time_shift_estimate.minutes} phút, lúc{" "}
                {formatEtaTime(result.time_shift_estimate.depart_time)}: khả
                năng có cổng tại trạm chính ước tính{" "}
                {formatPct(result.time_shift_estimate.p_available)}, tăng{" "}
                {(result.time_shift_estimate.improvement * 100).toFixed(1)} điểm
                %.
              </p>
              <p>
                Đây là gợi ý tham khảo, chưa đổi kế hoạch hoặc ghi thêm phân bổ.
              </p>
              <details>
                <summary>Giả định của gợi ý</summary>
                <ul>
                  {result.time_shift_estimate.assumptions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </details>
            </aside>
          ) : null}
        </>
      )}

      {result.reasons.length > 0 ? (
        hasPlan ? (
          <details className="plan-reasons">
            <summary>Vì sao kế hoạch này phù hợp?</summary>
            <ul className="reason-list">
              {result.reasons.map((reason) => (
                <li key={reason}>{displayReason(reason)}</li>
              ))}
            </ul>
          </details>
        ) : (
          <ul className="reason-list">
            {result.reasons.map((reason) => (
              <li key={reason}>{displayReason(reason)}</li>
            ))}
          </ul>
        )
      ) : null}

      <details className="tech-details">
        <summary>Cách tính &amp; độ tin cậy</summary>
        <p>
          Phần trăm cho biết khả năng còn ít nhất một cổng phù hợp khi bạn đến.
          Đây là dự báo, không phải xác nhận đặt chỗ.
        </p>
        <p>
          Pin khi đến là lượng pin ước tính còn lại sau quãng đường di chuyển.
          Đường vòng là quãng đường đi thêm để ghé trạm.
        </p>
        {result.plan_p_assumption === "independent_stations" ? (
          <p>
            Ước lượng cho cả kế hoạch dùng giả định hai trạm độc lập. Hai trạm
            có thể cùng đông khách nên xác suất thực tế có thể khác.
          </p>
        ) : null}
        <p>
          Nguồn trạng thái:{" "}
          {result.data_type === "simulated"
            ? "dữ liệu mô phỏng"
            : result.data_type === "real"
              ? "dữ liệu từ nguồn trạm"
              : "dữ liệu minh họa hoặc hỗn hợp"}
          .
        </p>
        <details className="verification-details">
          <summary>Thông tin kiểm chứng mô hình</summary>
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

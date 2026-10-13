import type { RecommendationResult } from "../../services/api";
import { DataTypeBadge } from "../../components/common/DataTypeBadge";
import { StationPlanCard } from "./StationPlanCard";

type Props = {
  result: RecommendationResult;
  stationNames?: Record<string, string>;
};

function formatPct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatEta(value: string): string {
  return new Date(value).toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  });
}

export function PlanSummary({ result, stationNames = {} }: Props) {
  const hasPlan = result.primary != null || result.backup != null;
  const primary = result.primary;
  const primaryName = primary
    ? (stationNames[primary.station_id] ?? primary.station_id)
    : null;

  return (
    <section
      className="plan-summary plan-summary--hero"
      aria-labelledby="plan-summary-title"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Kế hoạch sạc</p>
          <h2 id="plan-summary-title">Trạm đề xuất</h2>
        </div>
        <DataTypeBadge dataType={result.data_type} />
      </div>

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
              <dl className="plan-hero__metrics">
                <div>
                  <dt>Đến lúc</dt>
                  <dd>{formatEta(primary.eta)}</dd>
                </div>
                <div>
                  <dt>Khả năng có cổng</dt>
                  <dd data-probability={primary.p_available}>
                    {formatPct(primary.p_available)}
                  </dd>
                </div>
                {result.plan_p != null ? (
                  <div>
                    <dt>Ước lượng kế hoạch</dt>
                    <dd>{formatPct(result.plan_p)}</dd>
                  </div>
                ) : null}
              </dl>
              <p className="plan-hero__next">
                Bước tiếp: đi theo hướng trạm này trên bản đồ
                {result.backup
                  ? "; giữ trạm dự phòng nếu trạm chính đông."
                  : "."}
              </p>
            </div>
          ) : null}

          <div className="plan-grid">
            {primary ? (
              <StationPlanCard
                title="Chi tiết trạm chính"
                plan={primary}
                variant="primary"
                stationName={stationNames[primary.station_id]}
                compact
              />
            ) : null}
            {result.backup ? (
              <StationPlanCard
                title="Trạm dự phòng"
                plan={result.backup}
                variant="backup"
                stationName={stationNames[result.backup.station_id]}
              />
            ) : (
              <p className="status-message">Không có trạm dự phòng.</p>
            )}
          </div>
        </>
      )}

      {result.reasons.length > 0 ? (
        <ul className="reason-list">
          {result.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
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
          {result.backup ? (
            <p>Mã trạm dự phòng: {result.backup.station_id}</p>
          ) : null}
        </div>
      </details>
    </section>
  );
}

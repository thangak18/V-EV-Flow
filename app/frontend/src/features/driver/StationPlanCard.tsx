import type { Plan } from "../../services/api";

type Props = {
  title: string;
  plan: Plan;
  variant: "primary" | "backup";
  stationName?: string;
  /** Hide duplicate hero metrics when the plan already has a focus block. */
  compact?: boolean;
};

function formatProbability(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatEta(value: string): string {
  return new Date(value).toLocaleString("vi-VN");
}

export function StationPlanCard({
  title,
  plan,
  variant,
  stationName,
  compact = false,
}: Props) {
  return (
    <article className={`plan-card plan-card--${variant}`}>
      <header>
        <p className="eyebrow">{title}</p>
        {!compact ? <h3>{stationName ?? plan.station_id}</h3> : null}
      </header>
      <dl className="plan-metrics">
        {!compact ? (
          <>
            <div>
              <dt>Đến lúc (ETA)</dt>
              <dd>{formatEta(plan.eta)}</dd>
            </div>
            <div>
              <dt>Khả năng có cổng</dt>
              <dd data-probability={plan.p_available}>
                {formatProbability(plan.p_available)}
              </dd>
            </div>
          </>
        ) : null}
        <div>
          <dt>Pin lúc tới (SOC)</dt>
          <dd>{plan.arrival_soc_pct.toFixed(1)}%</dd>
        </div>
        <div>
          <dt>Khoảng cách</dt>
          <dd>{plan.distance_km.toFixed(1)} km</dd>
        </div>
        <div>
          <dt>Đường vòng thêm</dt>
          <dd>{plan.detour_km.toFixed(1)} km</dd>
        </div>
      </dl>
    </article>
  );
}

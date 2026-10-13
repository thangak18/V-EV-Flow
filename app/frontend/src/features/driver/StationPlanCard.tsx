import type { Plan } from "../../services/api";

type Props = {
  title: string;
  plan: Plan;
  variant: "primary" | "backup";
  stationName?: string;
};

function formatProbability(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function StationPlanCard({ title, plan, variant, stationName }: Props) {
  return (
    <article className={`plan-card plan-card--${variant}`}>
      <header>
        <p className="eyebrow">{title}</p>
        <h3>{stationName ?? plan.station_id}</h3>
        {stationName ? (
          <p className="plan-station-id">{plan.station_id}</p>
        ) : null}
      </header>
      <dl className="plan-metrics">
        <div>
          <dt>ETA</dt>
          <dd>{new Date(plan.eta).toLocaleString("vi-VN")}</dd>
        </div>
        <div>
          <dt>Arrival SOC</dt>
          <dd>{plan.arrival_soc_pct.toFixed(1)}%</dd>
        </div>
        <div>
          <dt>p_available at ETA</dt>
          <dd data-probability={plan.p_available}>
            {formatProbability(plan.p_available)}
          </dd>
        </div>
        <div>
          <dt>Distance</dt>
          <dd>{plan.distance_km.toFixed(1)} km</dd>
        </div>
        <div>
          <dt>Detour</dt>
          <dd>{plan.detour_km.toFixed(1)} km</dd>
        </div>
      </dl>
    </article>
  );
}

import type { RecommendationResult } from "../../services/api";
import { DataTypeBadge } from "../../components/common/DataTypeBadge";
import { StationPlanCard } from "./StationPlanCard";

type Props = {
  result: RecommendationResult;
};

export function PlanSummary({ result }: Props) {
  const hasPlan = result.primary != null || result.backup != null;

  return (
    <section className="plan-summary" aria-labelledby="plan-summary-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Charging plan</p>
          <h2 id="plan-summary-title">Recommendation</h2>
        </div>
        <DataTypeBadge dataType={result.data_type} />
      </div>

      {!hasPlan ? (
        <p className="status-message" role="status">
          No feasible station for this trip.
        </p>
      ) : (
        <div className="plan-grid">
          {result.primary ? (
            <StationPlanCard
              title="Primary"
              plan={result.primary}
              variant="primary"
            />
          ) : null}
          {result.backup ? (
            <StationPlanCard
              title="Backup"
              plan={result.backup}
              variant="backup"
            />
          ) : (
            <p className="status-message">No backup station available.</p>
          )}
        </div>
      )}

      <div className="plan-meta">
        {result.plan_p != null ? (
          <p>
            Combined plan estimate:{" "}
            <strong>{Math.round(result.plan_p * 100)}%</strong>
            {result.plan_p_assumption ? (
              <span className="assumption">
                {" "}
                (assumption: {result.plan_p_assumption})
              </span>
            ) : null}
          </p>
        ) : null}
        <p>
          Model {result.model_version} · allocation {result.allocation_method}
        </p>
        <ul className="reason-list">
          {result.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

import type { StrategyRow } from "../../hooks/useSimulationComparison";

type Props = {
  rows: StrategyRow[];
  meta?: { scenario: string; seed: number; vehicleCount: number } | null;
};

const LABELS: Record<string, string> = {
  nearest: "Nearest",
  currently_available: "Currently available",
  ai_allocation: "AI allocation",
};

export function StrategyComparison({ rows, meta }: Props) {
  if (rows.length === 0) {
    return (
      <p className="status-message" role="status">
        Run a comparison to see metrics for all three strategies.
      </p>
    );
  }

  return (
    <section className="strategy-comparison" aria-labelledby="strategy-title">
      <h2 id="strategy-title">Strategy comparison</h2>
      {meta ? (
        <p className="strategy-meta">
          Scenario {meta.scenario} · seed {meta.seed} · {meta.vehicleCount}{" "}
          vehicles. No hard-coded winner — numbers come from `/simulate`.
        </p>
      ) : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Strategy</th>
              <th scope="col">Success rate</th>
              <th scope="col">Mean detour km</th>
              <th scope="col">Mean wait min</th>
              <th scope="col">Failed</th>
              <th scope="col">Model / fixture</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) =>
              row.status === "success" ? (
                <tr key={row.strategy}>
                  <th scope="row">{LABELS[row.strategy] ?? row.strategy}</th>
                  <td>
                    {(row.result.metrics.success_rate * 100).toFixed(1)}%
                    <span
                      className="metric-bar"
                      style={{
                        width: `${row.result.metrics.success_rate * 100}%`,
                      }}
                      aria-hidden
                    />
                  </td>
                  <td>{row.result.metrics.mean_detour_km.toFixed(2)}</td>
                  <td>{row.result.metrics.mean_wait_minutes.toFixed(2)}</td>
                  <td>{row.result.metrics.failed_count}</td>
                  <td>
                    {row.result.model_version} ·{" "}
                    {row.result.fixture_hash.slice(0, 8)}
                  </td>
                </tr>
              ) : (
                <tr key={row.strategy} className="row-error">
                  <th scope="row">{LABELS[row.strategy] ?? row.strategy}</th>
                  <td colSpan={5}>Failed: {row.message}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

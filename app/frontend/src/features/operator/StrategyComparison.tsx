import type { StrategyRow } from "../../hooks/useSimulationComparison";

type Props = {
  rows: StrategyRow[];
  meta?: { scenario: string; seed: number; vehicleCount: number } | null;
};

const LABELS: Record<string, string> = {
  nearest: "Gần nhất",
  currently_available: "Đang trống",
  ai_allocation: "Phân bổ AI",
};

type SuccessRow = Extract<StrategyRow, { status: "success" }>;

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDeltaPct(value: number): string {
  const signed =
    value >= 0 ? `+${(value * 100).toFixed(1)}` : (value * 100).toFixed(1);
  return `${signed} điểm %`;
}

function formatDeltaKm(value: number): string {
  const signed = value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
  return `${signed} km`;
}

function formatDeltaMin(value: number): string {
  const signed = value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
  return `${signed} phút`;
}

function bestSuccess(rows: SuccessRow[]): SuccessRow | null {
  if (rows.length === 0) return null;
  return rows.reduce((best, row) =>
    row.result.metrics.success_rate > best.result.metrics.success_rate
      ? row
      : best,
  );
}

export function StrategyComparison({ rows, meta }: Props) {
  if (rows.length === 0) {
    return (
      <p className="status-message" role="status">
        Chạy so sánh để xem chỉ số của ba chiến lược.
      </p>
    );
  }

  const successRows = rows.filter(
    (row): row is SuccessRow => row.status === "success",
  );
  const baseline =
    successRows.find((row) => row.strategy === "nearest") ??
    successRows[0] ??
    null;
  const winner = bestSuccess(successRows);

  return (
    <section className="strategy-comparison" aria-labelledby="strategy-title">
      <h2 id="strategy-title">So sánh chiến lược</h2>
      {meta ? (
        <p className="strategy-meta">
          Kịch bản {meta.scenario} · {meta.vehicleCount} xe · seed {meta.seed}.
          Không chọn sẵn người thắng — số liệu từ mô phỏng.
        </p>
      ) : null}

      {winner && baseline && winner.strategy !== baseline.strategy ? (
        <p className="strategy-delta" data-testid="strategy-delta">
          So với{" "}
          <strong>{LABELS[baseline.strategy] ?? baseline.strategy}</strong>:{" "}
          <strong>{LABELS[winner.strategy] ?? winner.strategy}</strong> cao hơn{" "}
          {formatDeltaPct(
            winner.result.metrics.success_rate -
              baseline.result.metrics.success_rate,
          )}
          , đường vòng{" "}
          {formatDeltaKm(
            winner.result.metrics.mean_detour_km -
              baseline.result.metrics.mean_detour_km,
          )}
          , chờ{" "}
          {formatDeltaMin(
            winner.result.metrics.mean_wait_minutes -
              baseline.result.metrics.mean_wait_minutes,
          )}
          .
        </p>
      ) : winner ? (
        <p className="strategy-delta" data-testid="strategy-delta">
          Hiện tại <strong>{LABELS[winner.strategy] ?? winner.strategy}</strong>{" "}
          có tỷ lệ thành công cao nhất (
          {formatPct(winner.result.metrics.success_rate)}).
        </p>
      ) : null}

      <div className="strategy-cards">
        {rows.map((row) =>
          row.status === "success" ? (
            <article
              key={row.strategy}
              className={
                winner?.strategy === row.strategy
                  ? "strategy-card strategy-card--best"
                  : "strategy-card"
              }
              data-strategy={row.strategy}
            >
              <h3>{LABELS[row.strategy] ?? row.strategy}</h3>
              <p className="strategy-card__rate">
                {formatPct(row.result.metrics.success_rate)}
              </p>
              <p className="strategy-card__rate-label">Tỷ lệ thành công</p>
              <span
                className="metric-bar metric-bar--card"
                style={{
                  width: `${row.result.metrics.success_rate * 100}%`,
                }}
                aria-hidden
              />
              <dl className="strategy-card__metrics">
                <div>
                  <dt>Đường vòng</dt>
                  <dd>{row.result.metrics.mean_detour_km.toFixed(2)} km</dd>
                </div>
                <div>
                  <dt>Chờ trung bình</dt>
                  <dd>
                    {row.result.metrics.mean_wait_minutes.toFixed(2)} phút
                  </dd>
                </div>
                <div>
                  <dt>Thất bại</dt>
                  <dd>{row.result.metrics.failed_count}</dd>
                </div>
                {baseline && row.strategy !== baseline.strategy ? (
                  <div>
                    <dt>Δ thành công</dt>
                    <dd>
                      {formatDeltaPct(
                        row.result.metrics.success_rate -
                          baseline.result.metrics.success_rate,
                      )}
                    </dd>
                  </div>
                ) : null}
              </dl>
            </article>
          ) : (
            <article
              key={row.strategy}
              className="strategy-card strategy-card--error"
              data-strategy={row.strategy}
            >
              <h3>{LABELS[row.strategy] ?? row.strategy}</h3>
              <p className="strategy-card__error">Lỗi: {row.message}</p>
            </article>
          ),
        )}
      </div>

      <details className="tech-details">
        <summary>Chi tiết mô phỏng</summary>
        <div className="tech-details__body">
          {successRows.map((row) => (
            <p key={row.strategy}>
              {LABELS[row.strategy] ?? row.strategy}: {row.result.model_version}{" "}
              · fixture {row.result.fixture_hash.slice(0, 8)}
            </p>
          ))}
        </div>
      </details>
    </section>
  );
}

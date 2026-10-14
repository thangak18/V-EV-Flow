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

/** All success rows tied at the highest success rate (may be many). */
export function topSuccessRows(rows: SuccessRow[]): SuccessRow[] {
  if (rows.length === 0) return [];
  const best = Math.max(...rows.map((row) => row.result.metrics.success_rate));
  return rows.filter((row) => row.result.metrics.success_rate === best);
}

export function StrategyComparison({ rows, meta }: Props) {
  if (rows.length === 0) {
    return (
      <section className="strategy-comparison" aria-labelledby="strategy-title">
        <h2 id="strategy-title">So sánh chiến lược</h2>
        <div className="strategy-empty" role="status">
          <div className="strategy-empty__icon" aria-hidden>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect
                x="6"
                y="22"
                width="6"
                height="12"
                rx="1.5"
                fill="currentColor"
              />
              <rect
                x="17"
                y="14"
                width="6"
                height="20"
                rx="1.5"
                fill="currentColor"
              />
              <rect
                x="28"
                y="8"
                width="6"
                height="26"
                rx="1.5"
                fill="currentColor"
              />
            </svg>
          </div>
          <h3>Chưa có kết quả mô phỏng</h3>
          <p>
            Chọn kịch bản, seed và số xe rồi bấm So sánh 3 chiến lược. Ba chiến
            lược sẽ dùng cùng một tập xe.
          </p>
          <p className="strategy-empty__hint">
            Áp dụng kịch bản cập nhật bản đồ. So sánh chạy mô phỏng.
          </p>
        </div>
      </section>
    );
  }

  const successRows = rows.filter(
    (row): row is SuccessRow => row.status === "success",
  );
  const baseline =
    successRows.find((row) => row.strategy === "nearest") ??
    successRows[0] ??
    null;
  const leaders = topSuccessRows(successRows);
  const leaderIds = new Set(leaders.map((row) => row.strategy));
  const isTie = leaders.length > 1;

  return (
    <section className="strategy-comparison" aria-labelledby="strategy-title">
      <h2 id="strategy-title">So sánh chiến lược</h2>
      {meta ? (
        <p className="strategy-meta">
          Kịch bản {meta.scenario} · {meta.vehicleCount} xe · seed {meta.seed}.
          Không chọn sẵn người thắng — số liệu từ mô phỏng.
        </p>
      ) : null}

      {leaders.length === 0 ? null : isTie ? (
        <p className="strategy-delta" data-testid="strategy-delta">
          Đồng hạng tỷ lệ thành công cao nhất (
          {formatPct(leaders[0]!.result.metrics.success_rate)}):{" "}
          <strong>
            {leaders
              .map((row) => LABELS[row.strategy] ?? row.strategy)
              .join(", ")}
          </strong>
          .
        </p>
      ) : baseline && leaders[0]!.strategy !== baseline.strategy ? (
        <p className="strategy-delta" data-testid="strategy-delta">
          So với{" "}
          <strong>{LABELS[baseline.strategy] ?? baseline.strategy}</strong>:{" "}
          <strong>
            {LABELS[leaders[0]!.strategy] ?? leaders[0]!.strategy}
          </strong>{" "}
          cao hơn{" "}
          {formatDeltaPct(
            leaders[0]!.result.metrics.success_rate -
              baseline.result.metrics.success_rate,
          )}
          , đường vòng{" "}
          {formatDeltaKm(
            leaders[0]!.result.metrics.mean_detour_km -
              baseline.result.metrics.mean_detour_km,
          )}
          , chờ{" "}
          {formatDeltaMin(
            leaders[0]!.result.metrics.mean_wait_minutes -
              baseline.result.metrics.mean_wait_minutes,
          )}
          .
        </p>
      ) : (
        <p className="strategy-delta" data-testid="strategy-delta">
          Hiện tại{" "}
          <strong>
            {LABELS[leaders[0]!.strategy] ?? leaders[0]!.strategy}
          </strong>{" "}
          có tỷ lệ thành công cao nhất (
          {formatPct(leaders[0]!.result.metrics.success_rate)}).
        </p>
      )}

      <div className="strategy-bars" aria-label="Tỷ lệ thành công 0–100%">
        <p className="strategy-bars__scale">Tỷ lệ thành công (0–100%)</p>
        {rows.map((row) =>
          row.status === "success" ? (
            <div
              key={row.strategy}
              className={
                leaderIds.has(row.strategy)
                  ? "strategy-bar-row strategy-bar-row--best"
                  : "strategy-bar-row"
              }
              data-strategy={row.strategy}
            >
              <div className="strategy-bar-row__label">
                <strong>{LABELS[row.strategy] ?? row.strategy}</strong>
                <span>{formatPct(row.result.metrics.success_rate)}</span>
              </div>
              <div className="strategy-bar-row__track">
                <span
                  className="strategy-bar-row__fill"
                  style={{
                    width: `${row.result.metrics.success_rate * 100}%`,
                  }}
                />
              </div>
            </div>
          ) : (
            <div
              key={row.strategy}
              className="strategy-bar-row strategy-bar-row--error"
              data-strategy={row.strategy}
            >
              <div className="strategy-bar-row__label">
                <strong>{LABELS[row.strategy] ?? row.strategy}</strong>
                <span className="strategy-card__error">Lỗi: {row.message}</span>
              </div>
            </div>
          ),
        )}
      </div>

      <div className="table-wrap">
        <table className="strategy-metrics-table">
          <thead>
            <tr>
              <th scope="col">Chiến lược</th>
              <th scope="col">Đường vòng</th>
              <th scope="col">Chờ</th>
              <th scope="col">Thất bại</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) =>
              row.status === "success" ? (
                <tr
                  key={row.strategy}
                  className={
                    leaderIds.has(row.strategy) ? "row-best" : undefined
                  }
                >
                  <th scope="row">
                    {LABELS[row.strategy] ?? row.strategy}
                    {leaderIds.has(row.strategy) ? (
                      <span className="tie-badge">
                        {isTie ? " đồng hạng" : " cao nhất"}
                      </span>
                    ) : null}
                  </th>
                  <td>{row.result.metrics.mean_detour_km.toFixed(2)} km</td>
                  <td>
                    {row.result.metrics.mean_wait_minutes.toFixed(2)} phút
                  </td>
                  <td>{row.result.metrics.failed_count}</td>
                </tr>
              ) : (
                <tr key={row.strategy} className="row-error">
                  <th scope="row">{LABELS[row.strategy] ?? row.strategy}</th>
                  <td colSpan={3}>Lỗi: {row.message}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
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

import { useState } from "react";
import { useApiClient } from "../../app/useApiClient";
import {
  ApiError,
  type Scenario,
  type Station,
  type Strategy,
  type WhatIfResult,
} from "../../services/api";

const STRATEGIES: Record<Strategy, string> = {
  nearest: "Gần nhất",
  currently_available: "Đang trống",
  ai_allocation: "Phân bổ AI",
};
const SCENARIOS: Record<Scenario, string> = {
  normal: "Ngày thường",
  holiday_30_4: "Lễ 30/4",
  tet: "Tết",
};

export function WhatIfPanel({
  scenario,
  seed,
  vehicleCount,
  stations,
}: {
  scenario: Scenario;
  seed: number;
  vehicleCount: number;
  stations: Station[];
}) {
  const api = useApiClient();
  const [kind, setKind] = useState<"add_ports" | "shift_departures">(
    "add_ports",
  );
  const [station, setStation] = useState("");
  const [strategy, setStrategy] = useState<Strategy>("ai_allocation");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const stationId = station || stations[0]?.station_id || "";
  const canRun =
    Number.isInteger(seed) &&
    seed >= 0 &&
    Number.isInteger(vehicleCount) &&
    vehicleCount > 0 &&
    (kind === "shift_departures"
      ? vehicleCount >= 5
      : stations.some((item) => item.station_id === stationId));
  async function run() {
    if (pending || !canRun) return;
    setPending(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.whatif({
        scenario,
        seed,
        vehicle_count: vehicleCount,
        strategy,
        contract_version: "0.1.0",
        change:
          kind === "add_ports"
            ? { kind, station_id: stationId, ports: 2 }
            : { kind, fraction: 0.2, target_hour: 21 },
      });
      setResult(response);
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.code === "FEATURE_NOT_READY"
          ? "Chế độ hiện tại chưa bật what-if. Hãy chạy bản demo file/model/stateful."
          : cause instanceof Error
            ? cause.message
            : "Chưa chạy được what-if.",
      );
    } finally {
      setPending(false);
    }
  }
  const before = result?.before.metrics,
    after = result?.after.metrics;
  const delta = (value: number, unit: string) =>
    `${value > 0 ? "+" : ""}${value.toFixed(1)} ${unit}`;
  return (
    <section
      className="whatif-panel toolbar-card"
      aria-labelledby="whatif-title"
    >
      <h2 id="whatif-title">Thử thay đổi phương án (what-if)</h2>
      <p>
        Giữ cùng xe, seed và nhu cầu nền để so sánh trước/sau. Kết quả mô phỏng
        có thể tốt hơn hoặc kém đi.
      </p>
      <form
        className="whatif-controls"
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
      >
        <label>
          Thay đổi
          <select
            disabled={pending}
            value={kind}
            onChange={(event) => setKind(event.target.value as typeof kind)}
          >
            <option value="add_ports">Thêm 2 cổng tại một trạm</option>
            <option value="shift_departures">
              Dịch 20% xe sang 21:00–21:55
            </option>
          </select>
        </label>
        {kind === "add_ports" ? (
          <label>
            Trạm thử thêm cổng
            <select
              disabled={pending || stations.length === 0}
              value={stationId}
              onChange={(event) => setStation(event.target.value)}
            >
              {stations.length === 0 ? (
                <option value="">Chưa có danh mục trạm</option>
              ) : (
                stations.map((item) => (
                  <option key={item.station_id} value={item.station_id}>
                    {item.name}
                  </option>
                ))
              )}
            </select>
          </label>
        ) : (
          <p className="subtitle">
            Dịch giờ một nhóm xe foreground cố định; không thay nhu cầu nền.
          </p>
        )}
        <label>
          Chiến lược what-if
          <select
            disabled={pending}
            value={strategy}
            onChange={(event) => setStrategy(event.target.value as Strategy)}
          >
            {Object.entries(STRATEGIES).map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={pending || !canRun}>
          {pending ? "Đang so sánh what-if…" : "So sánh trước / sau"}
        </button>
      </form>
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
      {result && before && after ? (
        <div data-testid="whatif-result">
          <p>
            <strong>Dữ liệu mô phỏng</strong> ·{" "}
            {SCENARIOS[result.before.scenario]} ·{" "}
            {result.before.metrics.vehicle_count} xe · seed {result.before.seed}{" "}
            · {STRATEGIES[result.before.strategy]}
          </p>
          {result.change.kind === "add_ports" ? (
            <p className="status-message">
              Thêm {result.change.ports} cổng tại {result.change.station_id}. Dự
              báo ML giữ theo capacity gốc; chỉ simulator và xếp hạng dùng
              capacity mới, không phải model đã retrain.
            </p>
          ) : (
            <p className="status-message">
              Đã dịch {result.shifted_vehicle_count} xe sang khung{" "}
              {result.change.target_hour}:00–{result.change.target_hour}:55;
              tổng số xe giữ nguyên.
            </p>
          )}
          <div className="table-wrap">
            <table className="strategy-metrics-table">
              <thead>
                <tr>
                  <th>Chỉ số</th>
                  <th>Trước</th>
                  <th>Sau</th>
                  <th>Thay đổi</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>Có cổng ngay khi đến</th>
                  <td>{(before.success_rate * 100).toFixed(1)}%</td>
                  <td>{(after.success_rate * 100).toFixed(1)}%</td>
                  <td>
                    {delta(
                      (after.success_rate - before.success_rate) * 100,
                      "điểm %",
                    )}
                  </td>
                </tr>
                <tr>
                  <th>Thời gian chờ</th>
                  <td>{before.mean_wait_minutes.toFixed(1)} phút</td>
                  <td>{after.mean_wait_minutes.toFixed(1)} phút</td>
                  <td>
                    {delta(
                      after.mean_wait_minutes - before.mean_wait_minutes,
                      "phút",
                    )}
                  </td>
                </tr>
                <tr>
                  <th>Đường vòng</th>
                  <td>{before.mean_detour_km.toFixed(1)} km</td>
                  <td>{after.mean_detour_km.toFixed(1)} km</td>
                  <td>
                    {delta(after.mean_detour_km - before.mean_detour_km, "km")}
                  </td>
                </tr>
                <tr>
                  <th>Xe thất bại</th>
                  <td>{before.failed_count}</td>
                  <td>{after.failed_count}</td>
                  <td>{after.failed_count - before.failed_count}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <details className="tech-details">
            <summary>Giả định và giới hạn what-if</summary>
            <ul>
              {result.assumptions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p>
              Model: {result.after.model_version} · fixture{" "}
              {result.after.fixture_hash.slice(0, 8)}
            </p>
            <p>
              Cấu hình: {result.before_config_hash.slice(0, 8)} →{" "}
              {result.after_config_hash.slice(0, 8)}
            </p>
          </details>
        </div>
      ) : null}
    </section>
  );
}

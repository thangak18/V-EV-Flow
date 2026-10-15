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
          ? "Chế độ hiện tại chưa hỗ trợ đánh giá phương án. Cần kết nối bộ mô phỏng và mô hình dự báo."
          : cause instanceof Error
            ? cause.message
            : "Chưa đánh giá được phương án.",
      );
    } finally {
      setPending(false);
    }
  }
  const changedStationId =
    result?.change.kind === "add_ports" ? result.change.station_id : null;
  const before = result?.before.metrics,
    after = result?.after.metrics;
  const delta = (value: number, unit: string) =>
    `${value > 0 ? "+" : ""}${value.toFixed(1)} ${unit}`;
  return (
    <section
      className="whatif-panel toolbar-card"
      aria-labelledby="whatif-title"
    >
      <div className="section-step">
        <span>03</span>
        <div>
          <p className="eyebrow">LẬP KẾ HOẠCH NĂNG LỰC</p>
          <h2 id="whatif-title">Thử phương án cải thiện</h2>
        </div>
      </div>
      <p>
        Chọn một thay đổi để xem số xe có chỗ sạc và thời gian chờ trước / sau.
        Hai lượt dùng cùng nhóm xe và điều kiện trạm để so sánh công bằng.
      </p>
      <form
        className="whatif-controls"
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
      >
        <fieldset className="whatif-options">
          <legend>1. Chọn thay đổi muốn đánh giá</legend>
          <label
            className={`whatif-option ${kind === "add_ports" ? "whatif-option--selected" : ""}`}
          >
            <input
              type="radio"
              name="capacity-change"
              value="add_ports"
              aria-label="Bổ sung cổng sạc"
              aria-describedby="add-ports-description"
              checked={kind === "add_ports"}
              disabled={pending}
              onChange={() => setKind("add_ports")}
            />
            <span className="whatif-option__icon" aria-hidden>
              +2
            </span>
            <span>
              <strong>Bổ sung cổng sạc</strong>
              <small id="add-ports-description">
                Thêm 2 cổng tại một trạm để giảm nguy cơ thiếu chỗ.
              </small>
            </span>
          </label>
          <label
            className={`whatif-option ${kind === "shift_departures" ? "whatif-option--selected" : ""}`}
          >
            <input
              type="radio"
              name="capacity-change"
              value="shift_departures"
              aria-label="Chuyển xe sang giờ thấp điểm"
              aria-describedby="shift-hours-description"
              checked={kind === "shift_departures"}
              disabled={pending}
              onChange={() => setKind("shift_departures")}
            />
            <span className="whatif-option__icon" aria-hidden>
              21h
            </span>
            <span>
              <strong>Chuyển xe sang giờ thấp điểm</strong>
              <small id="shift-hours-description">
                Dời 20% xe sang 21:00–21:55; giữ nguyên tổng số xe.
              </small>
            </span>
          </label>
        </fieldset>
        <div className="whatif-parameters">
          <p className="eyebrow">2. THIẾT LẬP PHƯƠNG ÁN</p>
          {kind === "add_ports" ? (
            <label>
              Trạm cần bổ sung cổng
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
              Nhóm xe được chọn cố định từ mã lần chạy. Giờ xuất phát của các xe
              còn lại và điều kiện trạm không đổi.
            </p>
          )}
          <label>
            Phương thức điều phối
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
          <p className="whatif-scope">
            Phạm vi: toàn bộ {stations.length} trạm ·{" "}
            {vehicleCount > 0 ? vehicleCount : "—"} xe · {SCENARIOS[scenario]}.
            Bộ lọc bản đồ không thay đổi phạm vi mô phỏng.
          </p>
        </div>
        <div className="whatif-action">
          <p>3. Xem tác động dự kiến</p>
          <span>
            Một phương án có thể tốt hơn hoặc kém hơn. Kết quả không tự thay đổi
            cấu hình vận hành.
          </span>
          <button type="submit" disabled={pending || !canRun}>
            {pending ? "Đang đánh giá phương án…" : "So sánh trước / sau"}
          </button>
        </div>
      </form>
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
      {result && before && after ? (
        <div data-testid="whatif-result" className="whatif-result">
          <div className="whatif-result__headline">
            <div>
              <p className="eyebrow">KẾT QUẢ ĐÁNH GIÁ</p>
              <h3>
                {after.success_rate > before.success_rate
                  ? "Nhiều xe có chỗ sạc hơn"
                  : after.success_rate < before.success_rate
                    ? "Phương án làm giảm khả năng phục vụ"
                    : "Chưa ghi nhận cải thiện về số xe có chỗ"}
              </h3>
            </div>
            <span
              className={`delta-pill ${after.success_rate < before.success_rate ? "delta-pill--negative" : after.success_rate === before.success_rate ? "delta-pill--neutral" : ""}`}
            >
              {delta(
                (after.success_rate - before.success_rate) * 100,
                "điểm %",
              )}
            </span>
          </div>
          <div className="whatif-kpis">
            <article>
              <span>Có cổng ngay khi đến</span>
              <strong>
                <span className="whatif-value whatif-value--before">
                  {(before.success_rate * 100).toFixed(1)}%
                </span>{" "}
                <span aria-hidden>→</span>{" "}
                <span className="whatif-value">
                  {(after.success_rate * 100).toFixed(1)}%
                </span>
              </strong>
            </article>
            <article>
              <span>Thời gian chờ trung bình</span>
              <strong>
                {before.mean_wait_minutes.toFixed(1)} <span aria-hidden>→</span>{" "}
                {after.mean_wait_minutes.toFixed(1)} <small>phút</small>
              </strong>
            </article>
          </div>
          <p>
            <strong>Dữ liệu mô phỏng</strong> ·{" "}
            {SCENARIOS[result.before.scenario]} ·{" "}
            {result.before.metrics.vehicle_count} xe · mã lần chạy{" "}
            {result.before.seed} · {STRATEGIES[result.before.strategy]}
          </p>
          {result.change.kind === "add_ports" ? (
            <p className="status-message">
              Thêm {result.change.ports} cổng tại{" "}
              {stations.find(
                (station) => station.station_id === changedStationId,
              )?.name ?? result.change.station_id}
              .{" "}
              {result.prediction_mode === "capacity_retrained"
                ? "Đã dùng mô hình riêng phù hợp với số cổng mới. Kết quả thay đổi cả hạ tầng và mô hình dự báo."
                : "Dự báo vẫn dùng cấu hình trạm ban đầu. Số cổng mới chỉ áp dụng trong bộ mô phỏng và cách chọn trạm; mô hình chưa được huấn luyện lại."}
            </p>
          ) : (
            <p className="status-message">
              Đã dịch {result.shifted_vehicle_count} xe sang khung{" "}
              {result.change.target_hour}:00–{result.change.target_hour}:55;
              tổng số xe giữ nguyên.
            </p>
          )}
          <details className="whatif-breakdown">
            <summary>Xem đầy đủ chỉ số so sánh</summary>
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
                    <th>Quãng đường đi thêm</th>
                    <td>{before.mean_detour_km.toFixed(1)} km</td>
                    <td>{after.mean_detour_km.toFixed(1)} km</td>
                    <td>
                      {delta(
                        after.mean_detour_km - before.mean_detour_km,
                        "km",
                      )}
                    </td>
                  </tr>
                  <tr>
                    <th>Xe chưa được phục vụ</th>
                    <td>{before.failed_count}</td>
                    <td>{after.failed_count}</td>
                    <td>{after.failed_count - before.failed_count}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </details>
          <details className="tech-details">
            <summary>Cách so sánh &amp; nguồn dữ liệu</summary>
            <p>
              Hai phương án dùng cùng nhóm xe, mã lần chạy và điều kiện nền. Sự
              khác biệt đã chọn được áp dụng trong bộ mô phỏng; chưa thay đổi
              trạm ngoài thực tế.
            </p>
            <details className="verification-details">
              <summary>Thông tin kiểm chứng phép thử</summary>
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
          </details>
        </div>
      ) : null}
    </section>
  );
}

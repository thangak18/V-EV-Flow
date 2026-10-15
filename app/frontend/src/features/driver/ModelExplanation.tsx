import type { ModelExplanation as Explanation } from "../../services/api";

const LABELS: Record<string, string> = {
  ports_free: "Cổng trống hiện tại",
  ports_busy: "Cổng bận hiện tại",
  ports_broken: "Cổng hỏng hiện tại",
  horizon_minutes: "Số phút tới ETA",
  n_ports: "Tổng số cổng",
  power_kw: "Công suất trạm",
  hour_sin: "Giờ trong ngày (sin)",
  hour_cos: "Giờ trong ngày (cos)",
  weekday: "Thứ trong tuần",
  is_weekend: "Cuối tuần",
  is_holiday_scenario: "Kịch bản ngày lễ",
  scenario_normal: "Kịch bản ngày thường",
  scenario_holiday_30_4: "Kịch bản 30/4",
  scenario_tet: "Kịch bản Tết",
  station_type_urban: "Trạm nội đô",
  station_type_highway: "Trạm cao tốc",
  station_type_other: "Loại trạm khác",
};
function featureLabel(feature: string): string {
  const lag = /^(ports_free|ports_busy|ports_broken)_lag_(15|30|60)$/.exec(
    feature,
  );
  if (lag)
    return `${LABELS[lag[1]!]!.replace(" hiện tại", "")} ${lag[2]} phút trước`;
  const missing = /^lag_(15|30|60)_missing$/.exec(feature);
  return missing
    ? `Thiếu lịch sử ${missing[1]} phút`
    : (LABELS[feature] ?? feature);
}
export function ModelExplanation({
  explanation,
}: {
  explanation: Explanation;
}) {
  const top = [...explanation.features]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 5);
  const maximum = Math.max(
    ...top.map((item) => Math.abs(item.contribution)),
    1e-9,
  );
  return (
    <details
      className="tech-details shap-explanation"
      data-testid="shap-explanation"
    >
      <summary>Vì sao có xác suất này? (TreeSHAP)</summary>
      <p>
        5 đặc trưng ảnh hưởng nhất tới điểm LightGBM trước hiệu chỉnh. Đơn vị
        log-odds, không cộng trực tiếp vào % xác suất và không chứng minh quan
        hệ nhân quả.
      </p>
      <ul className="shap-features">
        {top.map((item) => (
          <li key={item.feature}>
            <div>
              <strong>{featureLabel(item.feature)}</strong>
              <span>
                {item.contribution > 0
                  ? "Tăng điểm"
                  : item.contribution < 0
                    ? "Giảm điểm"
                    : "Không đổi điểm"}{" "}
                {item.contribution > 0 ? "+" : ""}
                {item.contribution.toFixed(3)}
              </span>
            </div>
            <div className="shap-track" aria-hidden>
              <span
                className={
                  item.contribution >= 0 ? "shap-positive" : "shap-negative"
                }
                style={{
                  width: `${(Math.abs(item.contribution) / maximum) * 100}%`,
                }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="subtitle">
        Điểm nền {explanation.bias.toFixed(3)} → điểm model{" "}
        {explanation.raw_score.toFixed(3)}. Chỉ tổng của toàn bộ{" "}
        {explanation.features.length} đóng góp mới khớp điểm model; xác suất
        hiển thị đã qua calibrator.
      </p>
    </details>
  );
}

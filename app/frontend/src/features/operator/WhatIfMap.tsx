import { useState } from "react";
import { MapView } from "../../components/map/MapView";
import type { MapModel } from "../../components/map/types";
import type { Station, WhatIfResult } from "../../services/api";

/** Only capacity changes have station-level evidence. Simulation metrics are network-wide. */
export function WhatIfMap({
  result,
  stations,
}: {
  result: WhatIfResult;
  stations: Station[];
}) {
  const [phase, setPhase] = useState<"before" | "after">("after");
  const change = result.change;
  const metrics = result[phase].metrics;
  const target =
    change.kind === "add_ports"
      ? stations.find((station) => station.station_id === change.station_id)
      : undefined;
  const model: MapModel = {
    fitBounds: true,
    points: stations.map((station) => {
      const changed = station.station_id === target?.station_id;
      const ports =
        station.n_ports +
        (changed && phase === "after" && change.kind === "add_ports"
          ? change.ports
          : 0);
      return {
        id: station.station_id,
        lat: station.lat,
        lng: station.lng,
        role: "pressure",
        label: `${station.name} · ${ports} cổng`,
        color: changed ? "#7c3aed" : "#64748b",
        badge: changed
          ? phase === "after" && change.kind === "add_ports"
            ? `+${change.ports}`
            : `${ports}`
          : undefined,
      };
    }),
  };
  return (
    <section className="whatif-map" aria-label="Bản đồ so sánh phương án">
      <div className="whatif-map__head">
        <div>
          <h3>Thay đổi ở đâu trên mạng lưới?</h3>
          <p>
            {target
              ? `${target.name}: ${target.n_ports} → ${target.n_ports + (change.kind === "add_ports" ? change.ports : 0)} cổng.`
              : change.kind === "shift_departures"
                ? `${result.shifted_vehicle_count} xe đổi giờ xuất phát sang ${change.target_hour}:00–${change.target_hour}:55 trên toàn mạng lưới.`
                : "Không có tọa độ của trạm được thay đổi."}
          </p>
        </div>
        <div
          className="whatif-map__switch"
          role="group"
          aria-label="Chọn trước hoặc sau thay đổi"
        >
          <button
            type="button"
            aria-pressed={phase === "before"}
            onClick={() => setPhase("before")}
          >
            Trước thay đổi
          </button>
          <button
            type="button"
            aria-pressed={phase === "after"}
            onClick={() => setPhase("after")}
          >
            Sau thay đổi
          </button>
        </div>
      </div>
      <p className="whatif-map__summary" role="status">
        <strong>
          {phase === "before" ? "Trước thay đổi" : "Sau thay đổi"}
        </strong>{" "}
        · Toàn mạng lưới: {(metrics.success_rate * 100).toFixed(1)}% xe có cổng
        ngay khi đến · Chờ trung bình {metrics.mean_wait_minutes.toFixed(1)}{" "}
        phút.
      </p>
      <MapView model={model} preferFake={!import.meta.env.VITE_GOONG_MAP_KEY} />
      <p className="metric-note">
        {target
          ? "Trạm màu tím là nơi thử bổ sung cổng. Các trạm xám chỉ thể hiện vị trí."
          : "Các điểm thể hiện vị trí trạm; thay đổi giờ xe áp dụng trên toàn mạng lưới."}{" "}
        Chỉ số trước/sau là kết quả mô phỏng toàn mạng, chưa có kết quả riêng
        từng trạm; màu này không thể hiện nguy cơ hết chỗ.
      </p>
    </section>
  );
}

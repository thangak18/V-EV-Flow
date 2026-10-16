import { useCallback, useEffect, useMemo, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import { DataTypeBadge } from "../components/common/DataTypeBadge";
import { MapView } from "../components/map/MapView";
import type {
  MapModel,
  MapPoint,
  UnlocatedMapPoint,
} from "../components/map/types";
import { pressureColor } from "../features/operator/pressureColors";
import { PressureLegend } from "../features/operator/PressureLegend";
import { ScenarioSelector } from "../features/operator/ScenarioSelector";
import { SimulationControls } from "../features/operator/SimulationControls";
import { AreaFilter } from "../features/operator/AreaFilter";
import {
  inMonitoredArea,
  type MonitoredArea,
} from "../features/operator/areas";
import { WhatIfPanel } from "../features/operator/WhatIfPanel";
import { StrategyComparison } from "../features/operator/StrategyComparison";
import { isPlus07FiveMinuteBucket } from "../services/errors";
import { usePressure } from "../hooks/usePressure";
import { useSimulationComparison } from "../hooks/useSimulationComparison";
import type { Scenario, Station } from "../services/api";

export function OperatorPage() {
  const client = useApiClient();
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [time, setTime] = useState("2026-10-13T16:00:00+07:00");
  const [runtimeNotice, setRuntimeNotice] = useState("");
  const [runtimeReady, setRuntimeReady] = useState(false);
  const [placesAvailable, setPlacesAvailable] = useState(false);
  const [area, setArea] = useState<MonitoredArea | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    client
      .runtime(scenario, controller.signal)
      .then((context) => {
        if (controller.signal.aborted) return;
        if (context.observed_at) setTime(context.observed_at);
        setRuntimeNotice(
          !context.available
            ? "Chưa có dữ liệu phù hợp cho thời điểm đã chọn."
            : context.clock_mode === "replay"
              ? `Dữ liệu mô phỏng · Mốc quan sát ${context.observed_at ? new Date(context.observed_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }) : "chưa xác định"}`
              : context.message,
        );
        setRuntimeReady(context.available);
        setPlacesAvailable(context.places_available);
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setRuntimeNotice("Không lấy được thời gian/dữ liệu từ backend.");
      });
    return () => controller.abort();
  }, [client, scenario]);
  const [seed, setSeed] = useState(42);
  const [vehicleCount, setVehicleCount] = useState(100);
  const [draft, setDraft] = useState<{
    seed: number | null;
    count: number | null;
  }>({ seed: 42, count: 100 });
  const onDraftChange = useCallback(
    (nextSeed: number | null, nextCount: number | null) => {
      setDraft((previous) =>
        previous.seed === nextSeed && previous.count === nextCount
          ? previous
          : { seed: nextSeed, count: nextCount },
      );
    },
    [],
  );
  const [stations, setStations] = useState<Station[]>([]);
  const [directoryFailed, setDirectoryFailed] = useState(false);
  const pressure = usePressure();
  const simulation = useSimulationComparison();
  const forecastKey = `${scenario}|${time}`;
  const forecastReady = runtimeReady && isPlus07FiveMinuteBucket(time);
  const currentRequest = pressure.requestKey === forecastKey;
  const loadingForecast = currentRequest && pressure.status === "loading";
  const failedForecast = currentRequest && pressure.status === "error";
  const forecast =
    pressure.resultKey === forecastKey &&
    !failedForecast &&
    !loadingForecast &&
    runtimeReady
      ? pressure.result
      : null;
  const applyArea = (next: MonitoredArea | null) => {
    setArea(next);
    if (!forecastReady) return;
    // Pressure covers the whole network: radius changes reuse this same forecast.
    if (currentRequest && (loadingForecast || forecast)) return;
    void pressure.load(scenario, time);
  };

  useEffect(() => {
    const controller = new AbortController();
    client
      .listStations(controller.signal)
      .then((response) => {
        setStations(response.stations);
        setDirectoryFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setStations([]);
          setDirectoryFailed(true);
        }
      });
    return () => controller.abort();
  }, [client]);

  const stationIndex = useMemo(() => {
    return new Map(stations.map((station) => [station.station_id, station]));
  }, [stations]);

  const mapModel = useMemo<MapModel>(() => {
    const pressureStations = forecast?.stations ?? [];
    const points: MapPoint[] = [];
    const unlocated: UnlocatedMapPoint[] = [];

    for (const station of pressureStations) {
      const meta = stationIndex.get(station.station_id);
      if (meta && !inMonitoredArea(meta, area)) continue;
      const title = meta?.name ?? station.station_id;
      const label = `${title} · áp lực ${station.pressure_score.toFixed(2)}`;
      if (!meta) {
        if (area) continue;
        unlocated.push({
          id: station.station_id,
          label,
          role: "pressure",
        });
        continue;
      }
      points.push({
        id: station.station_id,
        lat: meta.lat,
        lng: meta.lng,
        label,
        role: "pressure",
        color: pressureColor(station.pressure_score),
      });
    }

    if (area)
      points.push({
        id: "monitored-area",
        lat: area.center.lat,
        lng: area.center.lng,
        label: `Khu vực theo dõi: ${area.center.label}`,
        role: "origin",
      });
    return { points, unlocated, fitBounds: true };
  }, [forecast, stationIndex, area]);

  const pressureDataType =
    forecast?.stations[0]?.data_type ?? ("mock" as const);

  const visibleStations = stations.filter((station) =>
    inMonitoredArea(station, area),
  );
  const visibleIds = new Set(
    visibleStations.map((station) => station.station_id),
  );
  const knownPressure = (forecast?.stations ?? []).filter((station) =>
    visibleIds.has(station.station_id),
  );
  const highRisk = knownPressure.filter(
    (station) => station.pressure_score >= 0.66,
  ).length;
  const availableAverage = knownPressure.length
    ? knownPressure.reduce((total, station) => total + station.p_available, 0) /
      knownPressure.length
    : null;
  const forecastPlaceholder = loadingForecast
    ? "Đang tải…"
    : failedForecast
      ? "Không tải được"
      : forecast
        ? "Chưa có dữ liệu"
        : "Chưa tải dự báo";
  const forecastHint = loadingForecast
    ? "Đang tính dự báo cho khu vực đã chọn."
    : failedForecast
      ? "Kết nối thất bại. Bấm Thử lại bên dưới."
      : forecast
        ? "Không có dự báo cho các trạm trong phạm vi này."
        : "Chọn khu vực rồi bấm Lọc khu vực, hoặc Toàn bộ mạng lưới.";
  return (
    <main className="operator-page">
      <header className="operator-header">
        <div>
          <p className="eyebrow">TỔNG QUAN MẠNG LƯỚI</p>
          <h2>Theo dõi & điều phối trạm sạc</h2>
          <p className="subtitle">
            Theo dõi nguy cơ thiếu chỗ, so sánh cách điều phối xe và đánh giá
            phương án cải thiện trước khi áp dụng.
          </p>
        </div>
        {forecast ? <DataTypeBadge dataType={pressureDataType} /> : null}
      </header>

      {runtimeNotice ? (
        <p className="status-message" role="status">
          {runtimeNotice}
        </p>
      ) : null}
      <AreaFilter
        stations={stations}
        placesAvailable={placesAvailable}
        onApply={applyArea}
        ready={forecastReady}
      />
      <div className="network-kpis" aria-label="Tổng quan khu vực">
        <article>
          <span>Trạm trong khu vực</span>
          <strong>
            {visibleStations.length}
            <small> / {stations.length}</small>
          </strong>
          <p>
            {area
              ? `Trong bán kính ${area.radiusKm} km`
              : "Toàn bộ mạng lưới có dữ liệu"}
          </p>
        </article>
        <article>
          <span>Trạm có nguy cơ hết chỗ</span>
          <strong className={knownPressure.length ? undefined : "kpi-status"}>
            {forecast && knownPressure.length ? (
              <>
                {highRisk}
                <small> trạm</small>
              </>
            ) : (
              forecastPlaceholder
            )}
          </strong>
          <p>
            {knownPressure.length
              ? `Dự báo sau 30 phút · trong ${knownPressure.length} trạm có dự báo`
              : forecastHint}
          </p>
          <details className="kpi-explanation">
            <summary>Cách xác định</summary>
            <p>
              Đếm các trạm được dự báo có nguy cơ hết chỗ từ 66% trở lên, tại
              thời điểm 30 phút sau mốc dữ liệu đang xem. Đây là ngưỡng cảnh báo
              do nhóm lựa chọn.
            </p>
            <p>
              0 trạm nghĩa là chưa có trạm nào chạm ngưỡng cảnh báo; không đảm
              bảo mọi trạm đều còn chỗ.
            </p>
          </details>
        </article>
        <article>
          <span>Khả năng còn chỗ trung bình</span>
          <strong
            className={availableAverage === null ? "kpi-status" : undefined}
          >
            {availableAverage === null
              ? forecastPlaceholder
              : `${Math.round(availableAverage * 100)}%`}
          </strong>
          <p>
            {knownPressure.length
              ? `Dự báo sau 30 phút · trung bình ${knownPressure.length} trạm`
              : forecastHint}
          </p>
        </article>
      </div>
      {area ? (
        <p className="scope-note">
          Khu vực: {area.center.label}.{" "}
          {visibleStations.length === 0
            ? "Chưa có dữ liệu trạm trong khu vực này. Bản đồ vẫn hiển thị vị trí bạn chọn; không suy diễn trạng thái trạm chưa có dữ liệu."
            : "Bộ lọc chỉ áp dụng cho bản đồ và tổng quan khu vực."}
        </p>
      ) : null}
      <div className="section-step">
        <span>02</span>
        <div>
          <h3>Đánh giá nhu cầu &amp; điều phối</h3>
          <p>
            Chọn điều kiện nhu cầu và số xe. Bản đồ cập nhật theo kịch bản; so
            sánh chiến lược sử dụng toàn bộ {stations.length} trạm trong mạng
            lưới.
          </p>
        </div>
      </div>
      <div className="operator-toolbar">
        <ScenarioSelector
          scenario={scenario}
          time={time}
          onScenarioChange={(next) => {
            if (next === scenario) return;
            setRuntimeReady(false);
            setScenario(next);
          }}
          onTimeChange={setTime}
          onApply={() => void pressure.load(scenario, time)}
          pending={pressure.status === "loading" || !runtimeReady}
        />
        <SimulationControls
          seed={seed}
          vehicleCount={vehicleCount}
          onSeedChange={setSeed}
          onVehicleCountChange={setVehicleCount}
          onRun={(nextSeed, nextVehicles) =>
            void simulation.run(scenario, nextSeed, nextVehicles)
          }
          pending={simulation.pending}
          onDraftChange={onDraftChange}
        />
      </div>

      {directoryFailed ? (
        <p className="status-message" role="status">
          Không tải được danh mục trạm — marker áp lực cần tọa độ danh mục.
        </p>
      ) : null}

      <div className="operator-workspace">
        <section className="operator-map-card">
          <div className="operator-map-card__head">
            <h3>Bản đồ khả năng phục vụ</h3>
            <p className="metric-note">
              Dự báo còn chỗ sau 30 phút kể từ mốc quan sát. Màu sắc không biểu
              thị số xe đang chờ.
            </p>
          </div>
          {loadingForecast ? (
            <p className="status-message" role="status">
              Đang tải dự báo cho khu vực đã chọn…
            </p>
          ) : null}
          {failedForecast ? (
            <div className="status-message error" role="alert">
              <p>{pressure.error ?? "Không tải được lớp áp lực."}</p>
              <button
                type="button"
                onClick={() => void pressure.load(scenario, time)}
              >
                Thử lại
              </button>
            </div>
          ) : null}
          <MapView
            model={mapModel}
            preferFake={!import.meta.env.VITE_GOONG_MAP_KEY}
          />
          <div className="operator-legend">
            <PressureLegend />
          </div>
          <p className="map-card-footer" role="status">
            {forecast
              ? `Đang hiển thị ${knownPressure.length} trạm có dự báo. Màu thể hiện nguy cơ không còn cổng khi xe đến.`
              : forecastHint}
          </p>
        </section>

        <section className="operator-results-card">
          <StrategyComparison rows={simulation.rows} meta={simulation.config} />
        </section>
      </div>
      <WhatIfPanel
        scenario={scenario}
        seed={draft.seed ?? -1}
        vehicleCount={draft.count ?? 0}
        stations={stations}
      />
    </main>
  );
}

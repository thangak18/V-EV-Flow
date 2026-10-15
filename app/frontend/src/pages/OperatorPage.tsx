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
import { WhatIfPanel } from "../features/operator/WhatIfPanel";
import { StrategyComparison } from "../features/operator/StrategyComparison";
import { usePressure } from "../hooks/usePressure";
import { useSimulationComparison } from "../hooks/useSimulationComparison";
import type { Scenario, Station } from "../services/api";

export function OperatorPage() {
  const client = useApiClient();
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [time, setTime] = useState("2026-10-13T16:00:00+07:00");
  const [runtimeNotice, setRuntimeNotice] = useState("");
  const [runtimeReady, setRuntimeReady] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    client
      .runtime(scenario, controller.signal)
      .then((context) => {
        if (controller.signal.aborted) return;
        if (context.observed_at) setTime(context.observed_at);
        setRuntimeNotice(context.message);
        setRuntimeReady(context.available);
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
    const pressureStations = pressure.result?.stations ?? [];
    const points: MapPoint[] = [];
    const unlocated: UnlocatedMapPoint[] = [];

    for (const station of pressureStations) {
      const meta = stationIndex.get(station.station_id);
      const title = meta?.name ?? station.station_id;
      const label = `${title} · áp lực ${station.pressure_score.toFixed(2)}`;
      if (!meta) {
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

    return { points, unlocated, fitBounds: true };
  }, [pressure.result, stationIndex]);

  const pressureDataType =
    pressure.result?.stations[0]?.data_type ?? ("mock" as const);

  return (
    <main className="operator-page">
      <header className="operator-header">
        <div>
          <h2>Áp lực trạm &amp; so sánh chiến lược</h2>
          <p className="subtitle">
            Áp lực là proxy rủi ro thiếu cổng, không phải số xe thực tế.
          </p>
        </div>
        {pressure.result ? <DataTypeBadge dataType={pressureDataType} /> : null}
      </header>

      {runtimeNotice ? (
        <p className="status-message" role="status">
          {runtimeNotice}
        </p>
      ) : null}
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
            <h3>Bản đồ trạm sạc</h3>
          </div>
          {pressure.status === "loading" ? (
            <p className="status-message" role="status">
              {pressure.stale
                ? "Đang làm mới lớp áp lực… vẫn hiện kết quả trước."
                : "Đang tải lớp áp lực…"}
            </p>
          ) : null}
          {pressure.status === "error" ? (
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
            {pressure.result
              ? "Bản đồ minh họa"
              : "Bấm Áp dụng kịch bản để xem lớp áp lực."}
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

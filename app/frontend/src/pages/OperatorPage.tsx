import { useEffect, useMemo, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import { AsyncState } from "../components/common/AsyncState";
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
import { StrategyComparison } from "../features/operator/StrategyComparison";
import { usePressure } from "../hooks/usePressure";
import { useSimulationComparison } from "../hooks/useSimulationComparison";
import type { Scenario, Station } from "../services/api";

export function OperatorPage() {
  const client = useApiClient();
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [time, setTime] = useState("2026-10-13T16:00:00+07:00");
  const [seed, setSeed] = useState(42);
  const [vehicleCount, setVehicleCount] = useState(100);
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
      const label = `${title} · pressure ${station.pressure_score.toFixed(2)}`;
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

  const dataType = pressure.result?.stations[0]?.data_type ?? ("mock" as const);

  return (
    <main className="operator-page">
      <header className="operator-header">
        <div>
          <p className="eyebrow">Operator</p>
          <h2>Pressure and strategy lab</h2>
          <p className="subtitle">
            Pressure là proxy rủi ro thiếu cổng — không phải xác suất bảo đảm.
          </p>
        </div>
        <DataTypeBadge dataType={dataType} />
      </header>

      <div className="operator-grid">
        <section className="operator-map">
          <AsyncState
            status={pressure.status}
            loadingMessage={
              pressure.stale
                ? "Refreshing pressure… showing last successful result."
                : "Loading pressure layer…"
            }
            emptyMessage="No pressure stations for this scenario/time."
            errorMessage={pressure.error ?? "Unable to load pressure."}
            onRetry={() => void pressure.load(scenario, time)}
            keepChildrenOnLoading={Boolean(pressure.result)}
          >
            <MapView
              model={mapModel}
              preferFake={!import.meta.env.VITE_GOONG_MAP_KEY}
            />
          </AsyncState>
        </section>

        <section className="operator-controls">
          <ScenarioSelector
            scenario={scenario}
            time={time}
            onScenarioChange={setScenario}
            onTimeChange={setTime}
            onApply={() => void pressure.load(scenario, time)}
            pending={pressure.status === "loading"}
          />
          <PressureLegend />
          <details className="operator-sim-details" open>
            <summary>100-vehicle simulation</summary>
            <SimulationControls
              seed={seed}
              vehicleCount={vehicleCount}
              onSeedChange={setSeed}
              onVehicleCountChange={setVehicleCount}
              onRun={(nextSeed, nextVehicles) =>
                void simulation.run(scenario, nextSeed, nextVehicles)
              }
              pending={simulation.pending}
            />
          </details>
          {directoryFailed ? (
            <p className="status-message" role="status">
              Station directory unavailable — pressure markers need directory
              coordinates.
            </p>
          ) : null}
        </section>
      </div>

      <StrategyComparison rows={simulation.rows} meta={simulation.config} />
    </main>
  );
}

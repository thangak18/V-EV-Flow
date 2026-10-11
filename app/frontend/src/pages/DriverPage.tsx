import { useEffect, useMemo, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import { AsyncState } from "../components/common/AsyncState";
import { DataTypeBadge } from "../components/common/DataTypeBadge";
import { MapView } from "../components/map/MapView";
import type { MapModel, MapPoint } from "../components/map/types";
import { CORRIDOR_PRESETS } from "../features/driver/corridorPresets";
import { DriverForm } from "../features/driver/DriverForm";
import { PlanSummary } from "../features/driver/PlanSummary";
import { useRecommendation } from "../hooks/useRecommendation";
import type { Station } from "../services/api";

export function DriverPage() {
  const client = useApiClient();
  const { status, result, error, submit, retry } = useRecommendation();
  const [stations, setStations] = useState<Station[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    client
      .listStations(controller.signal)
      .then((response) => setStations(response.stations))
      .catch(() => {
        /* map enrichment optional */
      });
    return () => controller.abort();
  }, [client]);

  const mapModel = useMemo<MapModel>(() => {
    const index = new Map(
      stations.map((station) => [station.station_id, station]),
    );
    const points: MapPoint[] = [
      {
        id: "origin",
        lat: CORRIDOR_PRESETS.hcm_vt.origin.lat,
        lng: CORRIDOR_PRESETS.hcm_vt.origin.lng,
        label: "Origin",
        role: "origin",
      },
      {
        id: "destination",
        lat: CORRIDOR_PRESETS.hcm_vt.destination.lat,
        lng: CORRIDOR_PRESETS.hcm_vt.destination.lng,
        label: "Destination",
        role: "destination",
      },
    ];

    if (result?.primary) {
      const meta = index.get(result.primary.station_id);
      points.push({
        id: result.primary.station_id,
        lat: meta?.lat ?? 10.55,
        lng: meta?.lng ?? 106.9,
        label: result.primary.station_id,
        role: "primary",
      });
    }
    if (result?.backup) {
      const meta = index.get(result.backup.station_id);
      points.push({
        id: result.backup.station_id,
        lat: meta?.lat ?? 10.45,
        lng: meta?.lng ?? 107.05,
        label: result.backup.station_id,
        role: "backup",
      });
    }
    return { points, fitBounds: true };
  }, [result, stations]);

  return (
    <main className="driver-page">
      <section className="driver-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Driver</p>
            <h2>Plan a charging stop</h2>
            <p className="subtitle">
              Explicit submit only — `/recommend` is never called on render.
            </p>
          </div>
          <DataTypeBadge dataType={result?.data_type ?? "mock"} />
        </div>

        <DriverForm pending={status === "loading"} onSubmit={submit} />

        <AsyncState
          status={status === "empty" ? "success" : status}
          loadingMessage="Building charging plan…"
          emptyMessage="No feasible station for this trip."
          errorMessage={error ?? "Unable to build a plan."}
          onRetry={retry}
        >
          {result ? <PlanSummary result={result} /> : null}
        </AsyncState>
      </section>

      <MapView
        model={mapModel}
        preferFake={!import.meta.env.VITE_GOONG_MAP_KEY}
      />
    </main>
  );
}

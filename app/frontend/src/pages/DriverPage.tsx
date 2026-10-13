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
import {
  CORRIDOR_PRESETS,
  type CorridorPresetId,
} from "../features/driver/corridorPresets";
import { DriverForm } from "../features/driver/DriverForm";
import { PlanSummary } from "../features/driver/PlanSummary";
import { useRecommendation } from "../hooks/useRecommendation";
import type { Station } from "../services/api";

export function DriverPage() {
  const client = useApiClient();
  const { status, result, error, submit, retry, clear } = useRecommendation();
  const [stations, setStations] = useState<Station[]>([]);
  const [directoryFailed, setDirectoryFailed] = useState(false);
  const [presetId, setPresetId] = useState<CorridorPresetId>("hcm_vt");

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

  const stationNames = useMemo(() => {
    return Object.fromEntries(
      stations.map((station) => [station.station_id, station.name]),
    );
  }, [stations]);

  const mapModel = useMemo<MapModel>(() => {
    const corridor = CORRIDOR_PRESETS[presetId];
    const index = new Map(
      stations.map((station) => [station.station_id, station]),
    );
    const points: MapPoint[] = [
      {
        id: "origin",
        lat: corridor.origin.lat,
        lng: corridor.origin.lng,
        label: "Điểm đi",
        role: "origin",
      },
      {
        id: "destination",
        lat: corridor.destination.lat,
        lng: corridor.destination.lng,
        label: "Điểm đến",
        role: "destination",
      },
    ];
    const unlocated: UnlocatedMapPoint[] = [];

    const placeStation = (
      stationId: string,
      role: "primary" | "backup",
    ): void => {
      const meta = index.get(stationId);
      const label = meta?.name ?? stationId;
      if (meta) {
        points.push({
          id: stationId,
          lat: meta.lat,
          lng: meta.lng,
          label,
          role,
        });
        return;
      }
      unlocated.push({
        id: stationId,
        label,
        role,
      });
    };

    if (result?.primary) placeStation(result.primary.station_id, "primary");
    if (result?.backup) placeStation(result.backup.station_id, "backup");

    return { points, unlocated, fitBounds: true };
  }, [presetId, result, stations]);

  function handlePresetChange(next: CorridorPresetId) {
    setPresetId(next);
    clear();
  }

  const hasResult = status === "success" && result != null;

  return (
    <main className={`driver-page${hasResult ? " driver-page--has-plan" : ""}`}>
      <section className="driver-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Tài xế</p>
            <h2>Lên kế hoạch dừng sạc</h2>
            <p className="subtitle">
              Chọn hành lang, pin hiện tại và đầu cắm — bấm tìm để nhận trạm đề
              xuất.
            </p>
          </div>
          <DataTypeBadge dataType={result?.data_type ?? "mock"} />
        </div>

        <DriverForm
          pending={status === "loading"}
          presetId={presetId}
          onPresetChange={handlePresetChange}
          onSubmit={submit}
        />

        {directoryFailed ? (
          <p className="status-message" role="status">
            Không tải được danh mục trạm — bản đồ có thể thiếu vị trí trạm.
          </p>
        ) : null}

        <AsyncState
          status={status === "empty" ? "success" : status}
          loadingMessage="Đang tìm kế hoạch sạc…"
          emptyMessage="Không có trạm khả thi cho chuyến này."
          errorMessage={error ?? "Không tạo được kế hoạch."}
          onRetry={retry}
        >
          {result ? (
            <PlanSummary result={result} stationNames={stationNames} />
          ) : null}
        </AsyncState>
      </section>

      <MapView
        model={mapModel}
        preferFake={!import.meta.env.VITE_GOONG_MAP_KEY}
      />
    </main>
  );
}

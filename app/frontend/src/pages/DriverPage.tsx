import { useEffect, useMemo, useRef, useState } from "react";

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
  DEFAULT_ORIGIN,
  DEFAULT_DESTINATION,
  tripLocations,
  type TripLocation,
} from "../features/driver/corridorPresets";
import { DriverForm } from "../features/driver/DriverForm";
import { PlanEmptyState, PlanSummary } from "../features/driver/PlanSummary";
import { useRecommendation } from "../hooks/useRecommendation";
import type {
  DataType,
  Station,
  Scenario,
  RuntimeContext,
} from "../services/api";

export function DriverPage() {
  const client = useApiClient();
  const { status, result, error, submit, retry, clear } = useRecommendation();
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [runtime, setRuntime] = useState<RuntimeContext>();
  const [runtimeLoading, setRuntimeLoading] = useState(true);
  const lastTime = useRef<string | null>(null);
  const [runtimeError, setRuntimeError] = useState("");
  const [resolvedOrigin, setResolvedOrigin] = useState<
    TripLocation | undefined
  >(DEFAULT_ORIGIN);
  const [resolvedDestination, setResolvedDestination] = useState<
    TripLocation | undefined
  >(DEFAULT_DESTINATION);
  useEffect(() => {
    const controller = new AbortController();
    const refresh = () =>
      client
        .runtime(scenario, controller.signal)
        .then((value) => {
          if (controller.signal.aborted) return;
          if (value.scenario !== scenario)
            throw new Error("runtime scenario mismatch");
          if (lastTime.current && lastTime.current !== value.observed_at)
            clear();
          lastTime.current = value.observed_at;
          setRuntimeLoading(false);
          setRuntime(value as RuntimeContext);
          setRuntimeError("");
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setRuntimeLoading(false);
            setRuntimeError(
              "Không lấy được thời gian/dữ liệu từ backend. Hãy tải lại trang.",
            );
          }
        });
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, 60000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [client, scenario, clear]);
  const [stations, setStations] = useState<Station[]>([]);
  const [directoryFailed, setDirectoryFailed] = useState(false);
  const [directoryDataType, setDirectoryDataType] = useState<DataType | null>(
    null,
  );
  const [origin, setOrigin] = useState(DEFAULT_ORIGIN.label);
  const [destination, setDestination] = useState(DEFAULT_DESTINATION.label);
  const locations = useMemo(() => tripLocations(stations), [stations]);

  useEffect(() => {
    const controller = new AbortController();
    client
      .listStations(controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setDirectoryDataType(response.data_type);
        setStations(response.stations);
        setDirectoryFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setStations([]);
          setDirectoryDataType(null);
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
    const selectedOrigin =
      (resolvedOrigin?.label === origin ? resolvedOrigin : undefined) ??
      locations.find((location) => location.label === origin);
    const selectedDestination =
      (resolvedDestination?.label === destination
        ? resolvedDestination
        : undefined) ??
      locations.find((location) => location.label === destination);
    const index = new Map(
      stations.map((station) => [station.station_id, station]),
    );
    const points: MapPoint[] = [];
    if (selectedOrigin)
      points.push({ id: "origin", ...selectedOrigin, role: "origin" });
    if (selectedDestination)
      points.push({
        id: "destination",
        ...selectedDestination,
        role: "destination",
      });
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
  }, [
    origin,
    destination,
    locations,
    result,
    stations,
    resolvedOrigin,
    resolvedDestination,
  ]);

  function handleLocationChange(
    field: "origin" | "destination",
    value: string,
  ) {
    if (field === "origin") {
      setOrigin(value);
      setResolvedOrigin(undefined);
    } else {
      setDestination(value);
      setResolvedDestination(undefined);
    }
    clear();
  }

  function focusMap() {
    document
      .querySelector<HTMLElement>('[data-testid="map-canvas"]')
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  const dataType = result?.data_type ?? directoryDataType;

  return (
    <main className="driver-page">
      <DriverForm
        pending={status === "loading"}
        locations={locations}
        origin={origin}
        destination={destination}
        onLocationChange={handleLocationChange}
        runtime={runtime}
        runtimeError={runtimeError}
        runtimeLoading={runtimeLoading}
        resolvedOrigin={resolvedOrigin}
        resolvedDestination={resolvedDestination}
        onResolveLocation={(field, location) => {
          if (field === "origin") {
            setResolvedOrigin(location);
            setOrigin(location.label);
          } else {
            setResolvedDestination(location);
            setDestination(location.label);
          }
          clear();
        }}
        onScenarioChange={(next) => {
          setScenario(next);
          setRuntime(undefined);
          setRuntimeLoading(true);
          clear();
        }}
        onSubmit={submit}
      />

      {directoryFailed ? (
        <p className="status-message" role="status">
          Không tải được danh mục trạm — bản đồ có thể thiếu vị trí trạm.
        </p>
      ) : null}

      <div className="driver-workspace">
        <aside className="driver-sidebar">
          {dataType ? (
            <div className="sidebar-badge-row">
              <DataTypeBadge dataType={dataType} />
            </div>
          ) : null}
          {status === "idle" ? (
            <PlanEmptyState />
          ) : (
            <AsyncState
              status={status === "empty" ? "success" : status}
              loadingMessage="Đang tìm kế hoạch sạc…"
              emptyMessage="Không có trạm khả thi cho chuyến này."
              errorMessage={error ?? "Không tạo được kế hoạch."}
              onRetry={retry}
            >
              {result ? (
                <PlanSummary
                  result={result}
                  stationNames={stationNames}
                  onFocusMap={focusMap}
                />
              ) : null}
            </AsyncState>
          )}
        </aside>

        <section className="driver-map">
          <MapView
            model={mapModel}
            preferFake={!import.meta.env.VITE_GOONG_MAP_KEY}
          />
        </section>
      </div>
    </main>
  );
}

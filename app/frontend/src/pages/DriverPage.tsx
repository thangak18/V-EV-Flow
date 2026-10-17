import { useEffect, useMemo, useRef, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import { AsyncState } from "../components/common/AsyncState";
import { cameraSummary } from "../components/common/cameraSummary";
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
import { useDriverRoutes } from "../hooks/useDriverRoutes";
import { useRecommendation } from "../hooks/useRecommendation";
import { useStationQueues } from "../hooks/useStationQueues";
import type {
  DataType,
  Station,
  Scenario,
  RuntimeContext,
} from "../services/api";

export function DriverPage() {
  const client = useApiClient();
  const { status, result, error, submit, retry, clear } = useRecommendation();
  const [routeDeparture, setRouteDeparture] = useState("");
  const [mapFocus, setMapFocus] = useState<{
    result: NonNullable<typeof result>;
    id: string;
    role: "primary" | "backup";
    sequence: number;
  }>();
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [runtime, setRuntime] = useState<RuntimeContext>();
  const [runtimeLoading, setRuntimeLoading] = useState(true);
  const lastTime = useRef<string | null>(null);
  const [runtimeError, setRuntimeError] = useState("");
  const [connectionAttempt, setConnectionAttempt] = useState(0);
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
              "Chưa kết nối được dữ liệu trạm. Vui lòng thử kết nối lại.",
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
  }, [client, scenario, clear, connectionAttempt]);
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
  }, [client, connectionAttempt]);

  const stationNames = useMemo(() => {
    return Object.fromEntries(
      stations.map((station) => [station.station_id, station.name]),
    );
  }, [stations]);

  const queues = useStationQueues(scenario, runtime?.observed_at).byStation;

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
      const plan = result?.[role];
      const probability = plan?.p_available;
      const probabilityLabel =
        probability == null
          ? ""
          : probability > 0.99 && probability < 1
            ? ">99%"
            : probability > 0 && probability < 0.01
              ? "<1%"
              : `${Math.round(probability * 100)}%`;
      if (meta) {
        const view = queues.get(stationId);
        points.push({
          id: stationId,
          lat: meta.lat,
          lng: meta.lng,
          label,
          role,
          camera: view ? cameraSummary(view) : undefined,
          description: result?.[role]
            ? `Khả năng còn cổng ${probabilityLabel} · Đến lúc ${new Date(result[role]!.eta).toLocaleTimeString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit" })} · Pin khi đến ${result[role]!.arrival_soc_pct.toFixed(1)}%. Dự báo tham khảo, chưa giữ chỗ.`
            : undefined,
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

    return {
      points,
      unlocated,
      fitBounds: true,
      focus:
        mapFocus && mapFocus.result === result
          ? {
              id: mapFocus.id,
              role: mapFocus.role,
              sequence: mapFocus.sequence,
            }
          : undefined,
    };
  }, [
    origin,
    destination,
    locations,
    result,
    stations,
    resolvedOrigin,
    resolvedDestination,
    mapFocus,
    queues,
  ]);

  const routeOrigin = mapModel.points.find((point) => point.role === "origin");
  const routeDestination = mapModel.points.find(
    (point) => point.role === "destination",
  );
  const routePrimary = mapModel.points.find(
    (point) => point.role === "primary",
  );
  const routeBackup = mapModel.points.find((point) => point.role === "backup");
  const coordinate = (point: MapPoint) => ({ lat: point.lat, lng: point.lng });
  const roadRoutes = useDriverRoutes(
    result?.primary && routeOrigin && routePrimary && routeDeparture
      ? [
          {
            id: "primary",
            label: "Điểm đi → trạm chính",
            color: "#146c52",
            origin: coordinate(routeOrigin),
            destination: coordinate(routePrimary),
            depart_time: routeDeparture,
          },
          ...(routeDestination
            ? [
                {
                  id: "onward",
                  label: "Trạm chính → điểm đến",
                  color: "#2563eb",
                  origin: coordinate(routePrimary),
                  destination: coordinate(routeDestination),
                  depart_time: result.primary.eta,
                },
              ]
            : []),
          ...(routeBackup
            ? [
                {
                  id: "backup",
                  label: "Nếu trạm chính hết chỗ → trạm dự phòng",
                  color: "#b45309",
                  dashed: true,
                  origin: coordinate(routePrimary),
                  destination: coordinate(routeBackup),
                  depart_time: result.primary.eta,
                },
              ]
            : []),
        ]
      : [],
  );

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

  function focusMap(role: "primary" | "backup") {
    const plan = result?.[role];
    if (
      !result ||
      !plan ||
      !mapModel.points.some(
        (point) => point.id === plan.station_id && point.role === role,
      )
    )
      return;
    setMapFocus((previous) => ({
      result,
      id: plan.station_id,
      role,
      sequence: (previous?.sequence ?? 0) + 1,
    }));
    document
      .querySelector<HTMLElement>('[data-testid="map-canvas"]')
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  const dataType = result?.data_type ?? directoryDataType;

  return (
    <main className="driver-page">
      <section className="page-intro driver-intro">
        <div>
          <p className="eyebrow">HÀNH TRÌNH CỦA BẠN</p>
          <h2>Chọn trạm sạc cho hành trình.</h2>
          <p>
            Chọn hành trình để tìm trạm phù hợp, xem pin khi đến và chuẩn bị một
            phương án dự phòng.
          </p>
        </div>
        <span className="intro-chip">
          <span aria-hidden>◈</span> Dự báo theo thời điểm đến
        </span>
      </section>
      <DriverForm
        pending={status === "loading"}
        locations={locations}
        origin={origin}
        destination={destination}
        onLocationChange={handleLocationChange}
        runtime={runtime}
        runtimeError={runtimeError}
        runtimeLoading={runtimeLoading}
        onRetryRuntime={() => {
          setRuntimeError("");
          setRuntimeLoading(true);
          setConnectionAttempt((value) => value + 1);
        }}
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
        onSubmit={(request) => {
          setRouteDeparture(request.depart_time);
          void submit(request);
        }}
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
                  queues={queues}
                  onFocusMap={focusMap}
                  canFocusPrimary={mapModel.points.some(
                    (point) => point.role === "primary",
                  )}
                  canFocusBackup={mapModel.points.some(
                    (point) => point.role === "backup",
                  )}
                />
              ) : null}
            </AsyncState>
          )}
        </aside>

        <section className="driver-map">
          <div className="driver-map-heading">
            <h3>Hành trình &amp; phương án sạc</h3>
            <p>A: Điểm đi · 1: Trạm chính · 2: Trạm dự phòng · B: Điểm đến</p>
          </div>
          {roadRoutes.loading ? (
            <p className="status-message" role="status">
              Đang tải tuyến đường thực tế…
            </p>
          ) : null}
          {roadRoutes.missing ? (
            <p className="status-message" role="status">
              Chưa tải đủ tuyến đường. Vị trí trạm và kế hoạch sạc vẫn hiển thị;
              không dùng đường nối thẳng để thay tuyến giao thông.
            </p>
          ) : null}
          <MapView
            model={{ ...mapModel, routes: roadRoutes.routes }}
            preferFake={!import.meta.env.VITE_GOONG_MAP_KEY}
          />
        </section>
      </div>
    </main>
  );
}

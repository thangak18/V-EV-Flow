import { useEffect, useMemo, useRef, useState } from "react";

import { FakeMapAdapter } from "./FakeMapAdapter";
import { GoongMapAdapter } from "./GoongMapAdapter";
import type {
  MapAdapter,
  MapModel,
  MapPoint,
  UnlocatedMapPoint,
} from "./types";

type Props = {
  model: MapModel;
  adapterFactory?: () => MapAdapter;
  preferFake?: boolean;
};

function hasGoongKey(): boolean {
  const key = import.meta.env.VITE_GOONG_MAP_KEY;
  return typeof key === "string" && key.trim().length > 0;
}

function defaultFactory(preferFake: boolean): MapAdapter {
  if (preferFake || import.meta.env.MODE === "test" || !hasGoongKey()) {
    return new FakeMapAdapter();
  }
  return new GoongMapAdapter();
}

export function MapView({ model, adapterFactory, preferFake = false }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const adapterRef = useRef<MapAdapter | null>(null);
  const latestModelRef = useRef(model);
  const [mapError, setMapError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [mounted, setMounted] = useState(false);
  const [dismissedFocus, setDismissedFocus] = useState<number>();
  const focusedPoint =
    model.focus &&
    model.points.find(
      (point) =>
        point.id === model.focus!.id && point.role === model.focus!.role,
    );
  const usingGoong = useMemo(
    () => !preferFake && hasGoongKey() && !adapterFactory,
    [preferFake, adapterFactory],
  );

  useEffect(() => {
    latestModelRef.current = model;
  }, [model]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    setMounted(false);
    setMapError(null);
    const adapter = adapterFactory?.() ?? defaultFactory(preferFake);
    adapterRef.current = adapter;

    Promise.resolve(adapter.mount(container, latestModelRef.current))
      .then(async () => {
        if (cancelled) return;
        setMapError(null);
        await adapter.update(latestModelRef.current);
        if (!cancelled) setMounted(true);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setMapError(
          cause instanceof Error ? cause.message : "Map failed to load",
        );
      });

    return () => {
      cancelled = true;
      adapter.destroy();
      adapterRef.current = null;
      setMounted(false);
    };
  }, [adapterFactory, preferFake, attempt]);

  useEffect(() => {
    const adapter = adapterRef.current;
    if (!adapter || mapError || !mounted) return;
    void Promise.resolve(adapter.update(latestModelRef.current)).catch(
      (cause: unknown) => {
        setMapError(
          cause instanceof Error ? cause.message : "Map failed to update",
        );
      },
    );
  }, [model, mapError, mounted]);

  const pointCount = model.points.length + (model.unlocated?.length ?? 0);

  return (
    <div className="map-panel">
      {!usingGoong ? (
        <p className="map-mode-banner" role="status">
          Bản đồ minh họa — Không dùng để dẫn đường
        </p>
      ) : (
        <p className="map-mode-banner map-mode-banner--live" role="status">
          Bản đồ Goong · tiles © Goong
        </p>
      )}
      {usingGoong && !mounted && !mapError ? (
        <p className="status-message" role="status">
          Đang tải bản đồ…
        </p>
      ) : null}
      <div className="map-stage">
        <div
          ref={containerRef}
          className="map-canvas"
          data-testid="map-canvas"
          aria-label="Bản đồ sạc"
        />
        {focusedPoint && model.focus?.sequence !== dismissedFocus ? (
          <aside
            className="map-focus-card"
            aria-live="polite"
            data-testid="station-map-info"
          >
            <span className="eyebrow">
              {focusedPoint.role === "backup" ? "TRẠM DỰ PHÒNG" : "TRẠM CHÍNH"}
            </span>
            <strong>{focusedPoint.label}</strong>
            {focusedPoint.description ? (
              <p>{focusedPoint.description}</p>
            ) : null}
            <button
              type="button"
              aria-label="Đóng thông tin trạm"
              onClick={() => setDismissedFocus(model.focus?.sequence)}
            >
              Đóng
            </button>
          </aside>
        ) : null}
      </div>
      {mapError ? (
        <div className="status-message error" role="alert">
          <p>
            Bản đồ lỗi:{" "}
            {mapError.includes("Timed out")
              ? "Kết nối bản đồ quá thời gian chờ"
              : mapError}
            . Vẫn xem được danh sách điểm bên dưới.
          </p>
          <button
            type="button"
            onClick={() => setAttempt((value) => value + 1)}
          >
            Tải lại bản đồ
          </button>
        </div>
      ) : null}
      {model.routes?.length ? (
        <ul className="map-route-legend" aria-label="Các tuyến đường">
          {model.routes.map((route) => (
            <li key={route.id}>
              <span
                style={{
                  borderColor: route.color,
                  borderTopStyle: route.dashed ? "dashed" : "solid",
                }}
                aria-hidden
              />
              {route.label}
            </li>
          ))}
        </ul>
      ) : null}
      <StationTextList
        points={model.points}
        unlocated={model.unlocated ?? []}
        defaultOpen={pointCount > 0 && pointCount <= 4}
      />
    </div>
  );
}

const ROLE_LABELS: Record<string, string> = {
  origin: "Điểm đi",
  destination: "Điểm đến",
  primary: "Trạm chính",
  backup: "Trạm dự phòng",
  pressure: "Áp lực",
};

function StationTextList({
  points,
  unlocated,
  defaultOpen,
}: {
  points: MapPoint[];
  unlocated: UnlocatedMapPoint[];
  defaultOpen: boolean;
}) {
  const count = points.length + unlocated.length;

  if (count === 0) {
    return (
      <p className="status-message" role="status">
        Chưa có điểm trên bản đồ.
      </p>
    );
  }

  // Remount when count / suggested open changes so initial open resets
  // without an effect-driven setState.
  return (
    <StationTextListBody
      key={`${count}-${defaultOpen ? "open" : "closed"}`}
      points={points}
      unlocated={unlocated}
      initialOpen={defaultOpen}
    />
  );
}

function StationTextListBody({
  points,
  unlocated,
  initialOpen,
}: {
  points: MapPoint[];
  unlocated: UnlocatedMapPoint[];
  initialOpen: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);
  const count = points.length + unlocated.length;

  return (
    <details
      className="map-station-details"
      open={open}
      onToggle={(event) => {
        setOpen(event.currentTarget.open);
      }}
    >
      <summary>Danh sách điểm trên bản đồ ({count})</summary>
      <ul className="map-text-list" aria-label="Station text list">
        {points.map((point) => (
          <li key={`${point.role}-${point.id}`}>
            <strong>{ROLE_LABELS[point.role] ?? point.role}</strong>:{" "}
            {point.label}
            {point.camera ? (
              <>
                {" "}
                <span
                  className="camera-badge"
                  role="img"
                  aria-label={`Có camera: ${point.camera}`}
                  title={point.camera}
                >
                  📹
                </span>
              </>
            ) : null}
            <span className="map-coord">
              {" "}
              ({point.lat.toFixed(4)}, {point.lng.toFixed(4)})
            </span>
          </li>
        ))}
        {unlocated.map((point) => (
          <li key={`unlocated-${point.role}-${point.id}`}>
            <strong>{ROLE_LABELS[point.role] ?? point.role}</strong>:{" "}
            {point.label} <span className="map-coord">(chưa có tọa độ)</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

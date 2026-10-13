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
  const [mounted, setMounted] = useState(false);
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
  }, [adapterFactory, preferFake]);

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
          Đang dùng bản đồ schematic (chưa bật bản đồ Goong).
        </p>
      ) : (
        <p className="map-mode-banner map-mode-banner--live" role="status">
          Bản đồ Goong · tiles © Goong
        </p>
      )}
      <div
        ref={containerRef}
        className="map-canvas"
        data-testid="map-canvas"
        aria-label="Bản đồ sạc"
      />
      {mapError ? (
        <p className="status-message error" role="alert">
          Bản đồ lỗi: {mapError}. Vẫn xem được danh sách điểm bên dưới.
        </p>
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

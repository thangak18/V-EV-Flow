import { useEffect, useMemo, useRef, useState } from "react";

import { FakeMapAdapter } from "./FakeMapAdapter";
import { GoongMapAdapter } from "./GoongMapAdapter";
import type { MapAdapter, MapModel, MapPoint } from "./types";

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
  const [mapError, setMapError] = useState<string | null>(null);
  const usingGoong = useMemo(
    () => !preferFake && hasGoongKey() && !adapterFactory,
    [preferFake, adapterFactory],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    const adapter = adapterFactory?.() ?? defaultFactory(preferFake);
    adapterRef.current = adapter;

    Promise.resolve(adapter.mount(container, model))
      .then(() => {
        if (!cancelled) setMapError(null);
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
    };
    // Mount once per adapter factory; updates handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adapterFactory, preferFake]);

  useEffect(() => {
    const adapter = adapterRef.current;
    if (!adapter || mapError) return;
    void Promise.resolve(adapter.update(model)).catch((cause: unknown) => {
      setMapError(
        cause instanceof Error ? cause.message : "Map failed to update",
      );
    });
  }, [model, mapError]);

  return (
    <div className="map-panel">
      {!usingGoong ? (
        <p className="map-mode-banner" role="status">
          Đang dùng schematic map (chưa có Goong tiles). Thêm{" "}
          <code>VITE_GOONG_MAP_KEY</code> vào <code>.env</code> ở root repo rồi
          restart Vite để hiện bản đồ Goong thật.
        </p>
      ) : (
        <p className="map-mode-banner map-mode-banner--live" role="status">
          Goong map · tiles © Goong
        </p>
      )}
      <div
        ref={containerRef}
        className="map-canvas"
        data-testid="map-canvas"
        aria-label="Charging map"
      />
      {mapError ? (
        <p className="status-message error" role="alert">
          Map unavailable: {mapError}. Textual station list remains usable.
        </p>
      ) : null}
      <StationTextList points={model.points} />
    </div>
  );
}

function StationTextList({ points }: { points: MapPoint[] }) {
  if (points.length === 0) {
    return (
      <p className="status-message" role="status">
        No map points yet.
      </p>
    );
  }

  return (
    <ul className="map-text-list" aria-label="Station text list">
      {points.map((point) => (
        <li key={`${point.role}-${point.id}`}>
          <strong>{point.role}</strong>: {point.label} ({point.lat.toFixed(4)},{" "}
          {point.lng.toFixed(4)})
        </li>
      ))}
    </ul>
  );
}

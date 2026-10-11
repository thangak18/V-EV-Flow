import { useCallback, useEffect, useRef, useState } from "react";

import type { ApiClient, Station } from "../services/api";

type Props = { client: Pick<ApiClient, "listStations"> };
type Status = "loading" | "success" | "empty" | "error";

export function MockStationList({ client }: Props) {
  const [status, setStatus] = useState<Status>("loading");
  const [stations, setStations] = useState<Station[]>([]);
  const [error, setError] = useState("Unable to load stations.");
  const controllerRef = useRef<AbortController | null>(null);

  const loadStations = useCallback(() => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus("loading");
    setError("Unable to load stations.");
    setStations([]);

    client
      .listStations(controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setStations(response.stations);
        setStatus(response.stations.length === 0 ? "empty" : "success");
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        setError(
          cause instanceof Error ? cause.message : "Unable to load stations.",
        );
        setStatus("error");
      });

    return () => controller.abort();
  }, [client]);

  useEffect(() => {
    // The request is the external synchronization this effect owns.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadStations();
    return () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [loadStations]);

  return (
    <section className="station-panel" aria-labelledby="station-list-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Station directory</p>
          <h2 id="station-list-title">Available stations</h2>
        </div>
        <span className="data-badge">Mock data</span>
      </div>

      {status === "loading" && (
        <p className="status-message" role="status">
          Loading stations…
        </p>
      )}
      {status === "error" && (
        <div className="status-message error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={loadStations}>
            Try again
          </button>
        </div>
      )}
      {status === "empty" && (
        <p className="status-message" role="status">
          No stations are available yet.
        </p>
      )}
      {status === "success" && (
        <ul className="station-list">
          {stations.map((station) => (
            <li className="station-card" key={station.station_id}>
              <div>
                <p className="station-id">{station.station_id}</p>
                <h3>{station.name}</h3>
                <p className="station-meta">
                  {station.network} · {station.station_type}
                </p>
              </div>
              <dl>
                <div>
                  <dt>Ports</dt>
                  <dd>{station.n_ports}</dd>
                </div>
                <div>
                  <dt>Power</dt>
                  <dd>{station.power_kw} kW</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

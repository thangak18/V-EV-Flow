import { useEffect, useMemo, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import type { QueueObservation, Scenario } from "../services/api";
import { isAbortError } from "../services/errors";

export type QueueStatus = "loading" | "success" | "error";

const NONE: ReadonlyMap<string, QueueObservation> = new Map();

type Loaded = {
  key: string;
  status: QueueStatus;
  byStation: ReadonlyMap<string, QueueObservation>;
};

/**
 * Camera queue views by station id. Cameras are optional context, so a failed
 * request leaves the map empty instead of blocking the page.
 */
export function useStationQueues(
  scenario: Scenario,
  observedAt: string | undefined,
) {
  const client = useApiClient();
  const key = `${scenario}|${observedAt ?? ""}`;
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    client
      .getStationQueues(
        { scenario, ...(observedAt ? { observed_at: observedAt } : {}) },
        controller.signal,
      )
      .then((response) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key,
          status: "success",
          byStation: new Map(
            response.observations.map((view) => [view.station_id, view]),
          ),
        });
      })
      .catch((cause: unknown) => {
        if (isAbortError(cause) || controller.signal.aborted) return;
        setLoaded({ key, status: "error", byStation: NONE });
      });
    return () => controller.abort();
  }, [client, scenario, observedAt, key]);

  return useMemo(
    () =>
      loaded && loaded.key === key
        ? { status: loaded.status, byStation: loaded.byStation }
        : { status: "loading" as QueueStatus, byStation: NONE },
    [loaded, key],
  );
}

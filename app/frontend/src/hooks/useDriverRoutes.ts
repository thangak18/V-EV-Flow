import { useEffect, useState } from "react";
import { useApiClient } from "../app/useApiClient";
import type { MapModel } from "../components/map/types";

type Route = NonNullable<MapModel["routes"]>[number];
type Leg = {
  id: string;
  label: string;
  color: string;
  dashed?: boolean;
  origin: { lat: number; lng: number };
  destination: { lat: number; lng: number };
  depart_time: string;
};

/** Read-only routes never create allocations; obsolete responses cannot redraw an edited plan. */
export function useDriverRoutes(legs: Leg[]) {
  const client = useApiClient();
  const key = JSON.stringify(legs);
  const [state, setState] = useState<{
    key: string;
    routes: Route[];
    missing: boolean;
  }>({ key: "", routes: [], missing: false });
  useEffect(() => {
    const controller = new AbortController();
    const requests: Leg[] = JSON.parse(key);
    if (!requests.length) return () => controller.abort();
    void Promise.all(
      requests.map(async (leg): Promise<Route | null> => {
        try {
          const alternatives = await client.getRoutes(
            {
              origin: leg.origin,
              destination: leg.destination,
              depart_time: leg.depart_time,
            },
            controller.signal,
          );
          const road = alternatives.find(
            (route) =>
              route.source === "goong-directions-v2" &&
              route.geometry &&
              route.geometry.length >= 2,
          );
          return road?.geometry
            ? {
                id: leg.id,
                label: leg.label,
                color: leg.color,
                dashed: leg.dashed,
                coordinates: road.geometry,
              }
            : null;
        } catch {
          return null;
        }
      }),
    ).then((results) => {
      if (!controller.signal.aborted)
        setState({
          key,
          routes: results.filter((route): route is Route => route !== null),
          missing: results.some((route) => !route),
        });
    });
    return () => controller.abort();
  }, [client, key]);
  return {
    routes: state.key === key ? state.routes : [],
    loading: legs.length > 0 && state.key !== key,
    missing: state.key === key && state.missing,
  };
}

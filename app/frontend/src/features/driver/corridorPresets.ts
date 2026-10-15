import type { Station } from "../../services/api";

export type TripLocation = { label: string; lat: number; lng: number };
export const DEFAULT_ORIGIN: TripLocation = {
  label: "TP. Hồ Chí Minh",
  lat: 10.78,
  lng: 106.7,
};
export const DEFAULT_DESTINATION: TripLocation = {
  label: "Vũng Tàu",
  lat: 10.35,
  lng: 107.08,
};

export function tripLocations(stations: Station[]): TripLocation[] {
  return [
    DEFAULT_ORIGIN,
    DEFAULT_DESTINATION,
    ...stations.map((station) => ({
      label: `${station.name} (${station.station_id})`,
      lat: station.lat,
      lng: station.lng,
    })),
  ];
}

export const DEFAULT_DEMO_TIME = "2026-10-13T16:00:00+07:00";

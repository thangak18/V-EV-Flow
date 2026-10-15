import type { Station } from "../../services/api";
import type { TripLocation } from "../driver/corridorPresets";

export type MonitoredArea = { center: TripLocation; radiusKm: number };

export function inMonitoredArea(
  station: Pick<Station, "lat" | "lng">,
  area: MonitoredArea | null,
): boolean {
  if (!area) return true;
  const radians = (degrees: number) => (degrees * Math.PI) / 180;
  const lat = radians(station.lat - area.center.lat);
  const lng = radians(station.lng - area.center.lng);
  const a =
    Math.sin(lat / 2) ** 2 +
    Math.cos(radians(area.center.lat)) *
      Math.cos(radians(station.lat)) *
      Math.sin(lng / 2) ** 2;
  return (
    6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a))) <=
    area.radiusKm
  );
}

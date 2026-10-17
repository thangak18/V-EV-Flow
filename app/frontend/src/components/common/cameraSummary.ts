import type { QueueObservation } from "../../services/api";

export const WEAK_CONFIDENCE = 0.6;

function clock(value: string): string {
  return new Date(value).toLocaleTimeString("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** One-line description reused by badges, map markers and tooltips. */
export function cameraSummary(observation: QueueObservation): string {
  const weak =
    observation.confidence < WEAK_CONFIDENCE ? " · tín hiệu yếu" : "";
  return (
    `Camera trạm (dữ liệu minh họa): ${observation.vehicles_waiting} xe chờ, ` +
    `${observation.vehicles_charging} xe đang sạc · cập nhật ${clock(observation.observed_at)} · ` +
    `độ tin cậy ${Math.round(observation.confidence * 100)}%${weak}`
  );
}

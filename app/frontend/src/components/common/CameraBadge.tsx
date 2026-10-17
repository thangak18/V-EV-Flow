import type { QueueObservation } from "../../services/api";
import { cameraSummary, WEAK_CONFIDENCE } from "./cameraSummary";

/** Camera icon with the queue count; renders nothing for a station without a camera. */
export function CameraBadge({
  observation,
}: {
  observation: QueueObservation | undefined;
}) {
  if (!observation) return null;
  const weak = observation.confidence < WEAK_CONFIDENCE;
  return (
    <span
      className={`camera-badge${weak ? " camera-badge--weak" : ""}`}
      role="img"
      aria-label={`Có camera: ${cameraSummary(observation)}`}
      title={cameraSummary(observation)}
    >
      <span aria-hidden>📹</span> {observation.vehicles_waiting} xe chờ
    </span>
  );
}

import type { DataType } from "../../services/api";

const LABELS: Record<DataType, string> = {
  mock: "Mock data",
  simulated: "Simulated data",
  real: "Real data",
  mixed: "Mixed data",
};

export function DataTypeBadge({ dataType }: { dataType: DataType }) {
  return (
    <span className={`data-badge data-badge--${dataType}`}>
      {LABELS[dataType]}
    </span>
  );
}

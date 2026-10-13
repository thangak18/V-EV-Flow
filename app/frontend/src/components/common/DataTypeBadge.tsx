import type { DataType } from "../../services/api";

const LABELS: Record<DataType, string> = {
  mock: "Dữ liệu minh họa",
  simulated: "Dữ liệu mô phỏng",
  real: "Dữ liệu thật",
  mixed: "Dữ liệu hỗn hợp",
};

export function DataTypeBadge({ dataType }: { dataType: DataType }) {
  return (
    <span className={`data-badge data-badge--${dataType}`}>
      {LABELS[dataType]}
    </span>
  );
}

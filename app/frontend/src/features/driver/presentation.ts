/** Translate known backend explanations; preserve unknown text rather than inventing a reason. */
const REASONS: Record<string, string> = {
  "Primary selected by configurable heuristic ranking after C3 feasibility.":
    "Trạm chính được chọn theo khả năng còn cổng, thời gian đi, mức pin và nhu cầu đã phân bổ.",
  "Plan ETA is a five-minute prediction bucket, not an exact physical arrival.":
    "ETA được làm tròn lên mốc 5 phút để dự báo; giờ đến thực tế có thể khác.",
  "Backup reachability uses cumulative distance without charging at primary.":
    "Pin đủ để đi tiếp từ trạm chính đến trạm dự phòng mà chưa cần sạc ở trạm chính.",
  "Backup ETA and probability were recomputed for the fallback journey.":
    "Giờ đến và xác suất tại trạm dự phòng tính theo hành trình đi tiếp từ trạm chính.",
  "Plan probability assumes independent stations, not guaranteed charging.":
    "Ước lượng kế hoạch giả định hai trạm độc lập; không bảo đảm chắc chắn có cổng.",
  "No reachable/eligible backup was found.":
    "Chưa tìm được trạm dự phòng phù hợp trong tầm pin và thời gian dự báo.",
  "No charging stations were available in the dataset.":
    "Chưa có trạm sạc trong nguồn dữ liệu đang dùng.",
  "No direct road route was available.":
    "Không tìm được đường đi cho hành trình này.",
  "No station-specific road route was available for some candidates.":
    "Một số trạm chưa có đường đi phù hợp.",
  "No onward road route was available to measure journey detour.":
    "Chưa tính được đường đi tiếp từ trạm tới điểm đến.",
  "Charging connector was incompatible.":
    "Đầu cắm của xe không phù hợp với trạm.",
  "Connector capacity was unknown.":
    "Chưa có đủ dữ liệu về số cổng đúng loại đầu cắm.",
  "No working charging capacity was available.":
    "Không còn cổng hoạt động phù hợp.",
  "Arrival SOC was insufficient.":
    "Pin khi đến trạm thấp hơn mức dự phòng cho phép.",
  "Prediction ETA exceeded the model horizon.":
    "Thời gian đến trạm vượt phạm vi dự báo của model.",
  "No feasible charging station was found.":
    "Chưa tìm được trạm phù hợp với hành trình và mức pin này.",
};

export function displayReason(reason: string): string {
  return REASONS[reason] ?? reason;
}

export function displayDistance(km: number): string {
  // Preserve short but nonzero travel rather than displaying a misleading 0 km.
  if (km === 0) return "0";
  if (km < 0.1) return "<0,1";
  return km < 10 ? km.toFixed(1).replace(".", ",") : km.toFixed(0);
}

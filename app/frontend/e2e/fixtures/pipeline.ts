/** Contract-shaped payloads for UI integration when HTTP facade is still Phase 0. */

export const PIPELINE_RECOMMEND = {
  request_id: "pipeline-e2e-001",
  primary: {
    station_id: "S012",
    eta: "2026-10-13T16:40:00+07:00",
    distance_km: 15,
    detour_km: 5,
    arrival_soc_pct: 15.5,
    p_available: 0.85,
  },
  backup: {
    station_id: "S013",
    eta: "2026-10-13T16:55:00+07:00",
    distance_km: 25,
    detour_km: 7.5,
    arrival_soc_pct: 12.5,
    p_available: 0.6,
  },
  plan_p: 0.94,
  plan_p_assumption: "independent_stations",
  reasons: ["Đủ pin để tới trạm chính và tiếp tục tới dự phòng nếu cần"],
  time_shift: null,
  model_version: "ranking-pipeline-v1",
  allocation_method: "ranking_penalty",
  data_type: "simulated",
  contract_version: "0.1.0",
} as const;

export const EMPTY_RECOMMEND = {
  request_id: "pipeline-e2e-empty",
  primary: null,
  backup: null,
  plan_p: null,
  plan_p_assumption: null,
  reasons: ["Không còn trạm khả thi trong tầm pin"],
  time_shift: null,
  model_version: "ranking-pipeline-v1",
  allocation_method: "ranking_penalty",
  data_type: "simulated",
  contract_version: "0.1.0",
} as const;

/** Primary id absent from station directory → map stays unlocated. */
export const UNLOCATED_RECOMMEND = {
  ...PIPELINE_RECOMMEND,
  request_id: "pipeline-e2e-unlocated",
  primary: {
    ...PIPELINE_RECOMMEND.primary,
    station_id: "S999",
  },
  backup: null,
} as const;

export function simulateResult(
  strategy: "nearest" | "currently_available" | "ai_allocation",
  successRate: number,
  opts: { scenario?: string; seed?: number; vehicleCount?: number } = {},
) {
  const scenario = opts.scenario ?? "normal";
  const seed = opts.seed ?? 42;
  const vehicleCount = opts.vehicleCount ?? 100;
  const failed = Math.round(vehicleCount * (1 - successRate));
  return {
    scenario,
    seed,
    strategy,
    model_version: "runner-e2e-v1",
    fixture_hash:
      "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    contract_version: "0.1.0",
    metrics: {
      success_rate: successRate,
      mean_detour_km: strategy === "ai_allocation" ? 1.8 : 2.5,
      mean_wait_minutes: strategy === "ai_allocation" ? 3.0 : 4.0,
      failed_count: failed,
      vehicle_count: vehicleCount,
    },
  };
}

import type { ModelExplanation, WhatIfResult } from "../services/api";
import { FIXTURE_HASH } from "./fixtureHash";

export const explanationFixture: ModelExplanation = {
  method: "tree_shap",
  space: "raw_margin_log_odds",
  bias: 0,
  raw_score: 0.3,
  raw_probability: 1 / (1 + Math.exp(-0.3)),
  calibrated_probability: 0.8,
  features: [
    { feature: "ports_free", value: 0, contribution: -0.2 },
    { feature: "horizon_minutes", value: 30, contribution: 0.5 },
  ],
};
export const whatIfFixture: WhatIfResult = {
  before: {
    scenario: "tet",
    seed: 42,
    strategy: "ai_allocation",
    model_version: "lightgbm-test",
    fixture_hash: FIXTURE_HASH,
    contract_version: "0.1.0",
    metrics: {
      success_rate: 0.8,
      mean_detour_km: 5,
      mean_wait_minutes: 8,
      failed_count: 10,
      vehicle_count: 100,
    },
  },
  after: {
    scenario: "tet",
    seed: 42,
    strategy: "ai_allocation",
    model_version: "lightgbm-test",
    fixture_hash: FIXTURE_HASH,
    contract_version: "0.1.0",
    metrics: {
      success_rate: 0.9,
      mean_detour_km: 5,
      mean_wait_minutes: 4,
      failed_count: 5,
      vehicle_count: 100,
    },
  },
  change: { kind: "add_ports", station_id: "S001", ports: 2 },
  before_config_hash: "b".repeat(64),
  after_config_hash: "c".repeat(64),
  shifted_vehicle_count: 0,
  data_type: "simulated",
  assumptions: [
    "Model giữ nguyên; đây là kết quả unit fixture, không phải đo thực tế.",
  ],
  contract_version: "0.1.0",
};

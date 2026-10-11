import { z } from "zod";

import { ApiError } from "./errors";

const DataTypeSchema = z.enum(["mock", "simulated", "real", "mixed"]);
const ScenarioSchema = z.enum(["normal", "holiday_30_4", "tet"]);
const StrategySchema = z.enum([
  "nearest",
  "currently_available",
  "ai_allocation",
]);

const StationSchema = z.object({
  station_id: z.string().min(1),
  name: z.string().min(1),
  lat: z.number().finite(),
  lng: z.number().finite(),
  n_ports: z.number().int().positive(),
  power_kw: z.number().positive(),
  connector_types: z.array(z.string()),
  network: z.string(),
  station_type: z.string(),
  source: z.string(),
  assumptions: z.array(z.string()),
});

const PlanSchema = z.object({
  station_id: z.string().min(1),
  eta: z.string().min(1),
  distance_km: z.number().finite(),
  detour_km: z.number().finite(),
  arrival_soc_pct: z.number().finite(),
  p_available: z.number().min(0).max(1),
});

const SimulationMetricsSchema = z.object({
  success_rate: z.number().finite(),
  mean_detour_km: z.number().finite(),
  mean_wait_minutes: z.number().finite(),
  failed_count: z.number().int().nonnegative(),
  vehicle_count: z.number().int().positive(),
});

export const StationListResponseSchema = z.object({
  stations: z.array(StationSchema),
  data_type: DataTypeSchema,
  source_notes: z.array(z.string()),
});

export const PredictionResultSchema = z.object({
  station_id: z.string().min(1),
  eta: z.string().min(1),
  p_available: z.number().min(0).max(1),
  reasons: z.array(z.string()),
  explanation_method: z.string(),
  model_version: z.string(),
  data_type: DataTypeSchema,
  contract_version: z.string(),
});

export const RecommendationResultSchema = z.object({
  request_id: z.string().min(1),
  primary: PlanSchema.nullable(),
  backup: PlanSchema.nullable(),
  plan_p: z.number().min(0).max(1).nullable().optional(),
  plan_p_assumption: z.string().nullable().optional(),
  reasons: z.array(z.string()),
  time_shift: z.number().nullable().optional(),
  model_version: z.string(),
  allocation_method: z.string(),
  data_type: DataTypeSchema,
  contract_version: z.string(),
});

export const PressureResponseSchema = z.object({
  time: z.string().min(1),
  scenario: ScenarioSchema,
  stations: z.array(
    z.object({
      station_id: z.string().min(1),
      p_available: z.number().min(0).max(1),
      pressure_score: z.number().finite(),
      data_type: DataTypeSchema,
    }),
  ),
  contract_version: z.string(),
});

export const SimulationResultSchema = z.object({
  scenario: ScenarioSchema,
  seed: z.number().int(),
  strategy: StrategySchema,
  model_version: z.string(),
  metrics: SimulationMetricsSchema,
  fixture_hash: z.string().min(1),
  contract_version: z.string(),
});

export const ResetResponseSchema = z.object({
  reset: z.boolean(),
  contract_version: z.string(),
});

export function parseApiResponse<S extends z.ZodType>(
  schema: S,
  body: unknown,
  label: string,
): z.output<S> {
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    throw ApiError.invalidResponse(
      `${label} failed contract validation`,
      parsed.error.issues,
    );
  }
  return parsed.data;
}

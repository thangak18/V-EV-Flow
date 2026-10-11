import { z } from "zod";

import { ApiError, isTimezoneAwareIso } from "./errors";

const DataTypeSchema = z.enum(["mock", "simulated", "real", "mixed"]);
const ScenarioSchema = z.enum(["normal", "holiday_30_4", "tet"]);
const StrategySchema = z.enum([
  "nearest",
  "currently_available",
  "ai_allocation",
]);

/** Mirror backend StrictModel(extra="forbid") + timezone-aware datetimes. */
const NonEmptyString = z.string().min(1);
const AwareIsoDateTime = z
  .string()
  .refine(isTimezoneAwareIso, "datetime must be timezone-aware ISO-8601");
const FixtureHashSchema = z
  .string()
  .regex(/^[0-9a-f]{64}$/, "fixture_hash must be lowercase sha256 hex");

const StationSchema = z.strictObject({
  station_id: NonEmptyString,
  name: NonEmptyString,
  lat: z.number().finite().min(-90).max(90),
  lng: z.number().finite().min(-180).max(180),
  n_ports: z.number().int().positive(),
  power_kw: z.number().positive(),
  connector_types: z.array(NonEmptyString).min(1),
  network: NonEmptyString,
  station_type: NonEmptyString,
  source: NonEmptyString,
  assumptions: z.array(z.string()),
});

const PlanSchema = z.strictObject({
  station_id: NonEmptyString,
  eta: AwareIsoDateTime,
  distance_km: z.number().finite().nonnegative(),
  detour_km: z.number().finite().nonnegative(),
  arrival_soc_pct: z.number().finite().min(0).max(100),
  p_available: z.number().min(0).max(1),
});

const SimulationMetricsSchema = z
  .strictObject({
    success_rate: z.number().finite().min(0).max(1),
    mean_detour_km: z.number().finite().nonnegative(),
    mean_wait_minutes: z.number().finite().nonnegative(),
    failed_count: z.number().int().nonnegative(),
    vehicle_count: z.number().int().nonnegative(),
  })
  .superRefine((metrics, ctx) => {
    if (metrics.failed_count > metrics.vehicle_count) {
      ctx.addIssue({
        code: "custom",
        message: "failed_count cannot exceed vehicle_count",
        path: ["failed_count"],
      });
    }
  });

export const StationListResponseSchema = z.strictObject({
  stations: z.array(StationSchema),
  data_type: DataTypeSchema,
  source_notes: z.array(z.string()),
});

export const PredictionResultSchema = z.strictObject({
  station_id: NonEmptyString,
  eta: AwareIsoDateTime,
  p_available: z.number().min(0).max(1),
  reasons: z.array(z.string()),
  explanation_method: NonEmptyString,
  model_version: NonEmptyString,
  data_type: DataTypeSchema,
  contract_version: NonEmptyString,
});

export const RecommendationResultSchema = z.strictObject({
  request_id: NonEmptyString,
  primary: PlanSchema.nullable(),
  backup: PlanSchema.nullable(),
  plan_p: z.number().min(0).max(1).nullable().optional(),
  plan_p_assumption: z.string().nullable().optional(),
  reasons: z.array(z.string()),
  time_shift: z.number().int().nullable().optional(),
  model_version: NonEmptyString,
  allocation_method: NonEmptyString,
  data_type: DataTypeSchema,
  contract_version: NonEmptyString,
});

export const PressureResponseSchema = z.strictObject({
  time: AwareIsoDateTime,
  scenario: ScenarioSchema,
  stations: z.array(
    z.strictObject({
      station_id: NonEmptyString,
      p_available: z.number().min(0).max(1),
      pressure_score: z.number().min(0).max(1),
      data_type: DataTypeSchema,
    }),
  ),
  contract_version: NonEmptyString,
});

export const SimulationResultSchema = z.strictObject({
  scenario: ScenarioSchema,
  seed: z.number().int(),
  strategy: StrategySchema,
  model_version: NonEmptyString,
  metrics: SimulationMetricsSchema,
  fixture_hash: FixtureHashSchema,
  contract_version: NonEmptyString,
});

export const ResetResponseSchema = z.strictObject({
  reset: z.boolean(),
  contract_version: NonEmptyString,
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

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

export const ModelExplanationSchema = z
  .strictObject({
    method: z.literal("tree_shap"),
    space: z.literal("raw_margin_log_odds"),
    bias: z.number().finite(),
    raw_score: z.number().finite(),
    raw_probability: z.number().min(0).max(1),
    calibrated_probability: z.number().min(0).max(1),
    features: z
      .array(
        z.strictObject({
          feature: NonEmptyString,
          value: z.number().finite(),
          contribution: z.number().finite(),
        }),
      )
      .min(1),
  })
  .superRefine((explanation, context) => {
    const sum =
      explanation.bias +
      explanation.features.reduce(
        (value, item) => value + item.contribution,
        0,
      );
    if (Math.abs(sum - explanation.raw_score) > 1e-5)
      context.addIssue({
        code: "custom",
        message: "TreeSHAP does not reconstruct the raw margin",
      });
  });

const TimeShiftEstimateSchema = z.strictObject({
  minutes: z.number().int().positive().max(60).multipleOf(5),
  station_id: NonEmptyString,
  depart_time: AwareIsoDateTime,
  eta: AwareIsoDateTime,
  p_available: z.number().min(0).max(1),
  improvement: z.number().positive().max(1),
  assumptions: z.array(z.string()).min(1),
});

const PlanSchema = z.strictObject({
  station_id: NonEmptyString,
  eta: AwareIsoDateTime,
  distance_km: z.number().finite().nonnegative(),
  detour_km: z.number().finite().nonnegative(),
  arrival_soc_pct: z.number().finite().min(0).max(100),
  p_available: z.number().min(0).max(1),
  explanation: ModelExplanationSchema.nullable().optional(),
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

/** Validated subset of the existing dictionary-shaped /ready response. */
export const RuntimeStatusSchema = z.object({
  ready: z.boolean(),
  data_backend: z.enum(["mock", "file", "real"]),
  predictor_backend: z.enum(["fake", "model"]),
  route_backend: z.enum(["fake", "goong"]),
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
  explanation: ModelExplanationSchema.nullable().optional(),
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
  time_shift: z
    .number()
    .int()
    .positive()
    .max(60)
    .multipleOf(5)
    .nullable()
    .optional(),
  time_shift_estimate: TimeShiftEstimateSchema.nullable().optional(),
  time_shift_evaluated: z.boolean().nullable().optional(),
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

export const WhatIfResultSchema = z
  .strictObject({
    before: SimulationResultSchema,
    after: SimulationResultSchema,
    change: z.discriminatedUnion("kind", [
      z.strictObject({
        kind: z.literal("add_ports"),
        station_id: NonEmptyString,
        ports: z.number().int().min(1).max(20),
      }),
      z.strictObject({
        kind: z.literal("shift_departures"),
        fraction: z.number().positive().max(1),
        target_hour: z.number().int().min(20).max(21),
      }),
    ]),
    before_config_hash: FixtureHashSchema,
    after_config_hash: FixtureHashSchema,
    shifted_vehicle_count: z.number().int().nonnegative(),
    data_type: z.literal("simulated"),
    assumptions: z.array(z.string()).min(1),
    contract_version: z.literal("0.1.0"),
  })
  .superRefine((result, context) => {
    for (const key of [
      "scenario",
      "seed",
      "strategy",
      "fixture_hash",
      "model_version",
      "contract_version",
    ] as const) {
      if (result.before[key] !== result.after[key])
        context.addIssue({
          code: "custom",
          message: `what-if ${key} mismatch`,
        });
    }
    if (
      result.before.metrics.vehicle_count !==
        result.after.metrics.vehicle_count ||
      result.shifted_vehicle_count > result.before.metrics.vehicle_count
    )
      context.addIssue({
        code: "custom",
        message: "what-if population mismatch",
      });
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

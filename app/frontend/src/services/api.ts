import type { components, operations } from "../types/api.generated";

import { ApiError, isAbortError } from "./errors";
import {
  parseApiResponse,
  MapRoutesSchema,
  PlaceSuggestionsSchema,
  PlaceLocationSchema,
  RuntimeContextSchema,
  PredictionResultSchema,
  PressureResponseSchema,
  RecommendationResultSchema,
  ResetResponseSchema,
  RuntimeStatusSchema,
  WhatIfResultSchema,
  SimulationResultSchema,
  StationListResponseSchema,
} from "./schemas";

export { ApiError } from "./errors";

type JsonBody<TOperation extends keyof operations> =
  operations[TOperation]["requestBody"] extends {
    content: { "application/json": infer TBody };
  }
    ? TBody
    : never;

type JsonResponse<TOperation extends keyof operations> =
  operations[TOperation] extends {
    responses: { 200: { content: { "application/json": infer TResponse } } };
  }
    ? TResponse
    : never;

export class ApiClient {
  private readonly baseUrl: string;

  constructor(
    baseUrl: string,
    private readonly fetcher: typeof fetch = (...args) => fetch(...args),
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  getRoutes(body: components["schemas"]["RouteRequest"], signal?: AbortSignal) {
    return this.request("/routes", { method: "POST", body, signal }).then(
      (response) => parseApiResponse(MapRoutesSchema, response, "mapRoutes"),
    );
  }

  runtime(scenario: Scenario, signal?: AbortSignal) {
    return this.request(`/runtime?scenario=${encodeURIComponent(scenario)}`, {
      signal,
    }).then((body) =>
      parseApiResponse(RuntimeContextSchema, body, "runtimeContext"),
    );
  }

  searchPlaces(query: string, session: string, signal?: AbortSignal) {
    const params = new URLSearchParams({ q: query, session });
    return this.request(`/places/search?${params}`, { signal }).then((body) =>
      parseApiResponse(PlaceSuggestionsSchema, body, "searchPlaces"),
    );
  }

  resolvePlace(placeId: string, session: string, signal?: AbortSignal) {
    const params = new URLSearchParams({ place_id: placeId, session });
    return this.request(`/places/detail?${params}`, { signal }).then((body) =>
      parseApiResponse(PlaceLocationSchema, body, "resolvePlace"),
    );
  }

  ready(signal?: AbortSignal) {
    return this.request("/ready", { signal }).then((body) =>
      parseApiResponse(RuntimeStatusSchema, body, "ready"),
    );
  }

  listStations(signal?: AbortSignal): Promise<JsonResponse<"listStations">> {
    return this.request("/stations", { signal }).then((body) =>
      parseApiResponse(StationListResponseSchema, body, "listStations"),
    );
  }

  predict(
    body: JsonBody<"predictAvailability">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"predictAvailability">> {
    return this.request("/predict", { method: "POST", body, signal }).then(
      (response) =>
        parseApiResponse(PredictionResultSchema, response, "predict"),
    );
  }

  recommend(
    body: JsonBody<"recommendStation">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"recommendStation">> {
    return this.request("/recommend", { method: "POST", body, signal }).then(
      (response) =>
        parseApiResponse(
          RecommendationResultSchema,
          response,
          "recommend",
        ) as JsonResponse<"recommendStation">,
    );
  }

  getPressure(
    query: operations["getPressure"]["parameters"]["query"],
    signal?: AbortSignal,
  ): Promise<JsonResponse<"getPressure">> {
    const params = new URLSearchParams({
      scenario: query.scenario,
      time: query.time,
    });
    return this.request(`/pressure?${params}`, { signal }).then((response) =>
      parseApiResponse(PressureResponseSchema, response, "getPressure"),
    );
  }

  /** @deprecated Prefer getPressure; kept for Phase 0 call sites. */
  pressure(
    query: operations["getPressure"]["parameters"]["query"],
    signal?: AbortSignal,
  ): Promise<JsonResponse<"getPressure">> {
    return this.getPressure(query, signal);
  }

  simulate(
    body: JsonBody<"simulate">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"simulate">> {
    return this.request("/simulate", { method: "POST", body, signal }).then(
      (response) =>
        parseApiResponse(SimulationResultSchema, response, "simulate"),
    );
  }

  whatif(
    body: JsonBody<"whatIf">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"whatIf">> {
    return this.request("/whatif", { method: "POST", body, signal }).then(
      (response) => {
        // Runtime parsing is mandatory; strictNullChecks=false widens Zod union output.
        const result = parseApiResponse(
          WhatIfResultSchema,
          response,
          "whatif",
        ) as JsonResponse<"whatIf">;
        const before = result.before;
        const expected = body.change;
        const actual = result.change;
        const changeMatches =
          expected.kind === "add_ports" && actual.kind === "add_ports"
            ? expected.station_id === actual.station_id &&
              expected.ports === actual.ports
            : expected.kind === "shift_departures" &&
              actual.kind === "shift_departures" &&
              expected.fraction === actual.fraction &&
              expected.target_hour === actual.target_hour;
        if (
          before.scenario !== body.scenario ||
          before.seed !== body.seed ||
          before.strategy !== body.strategy ||
          before.metrics.vehicle_count !== body.vehicle_count ||
          !changeMatches
        ) {
          throw ApiError.invalidResponse(
            "what-if response does not match the requested experiment",
          );
        }
        return result;
      },
    );
  }

  reset(
    body: JsonBody<"resetDemo">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"resetDemo">> {
    return this.request("/reset", { method: "POST", body, signal }).then(
      (response) => parseApiResponse(ResetResponseSchema, response, "reset"),
    );
  }

  private async request(
    path: string,
    options: {
      method?: "POST";
      body?: unknown;
      signal?: AbortSignal;
    } = {},
  ): Promise<unknown> {
    let response: Response;
    try {
      response = await this.fetcher(`${this.baseUrl}${path}`, {
        method: options.method,
        headers:
          options.body === undefined
            ? undefined
            : { "Content-Type": "application/json" },
        body:
          options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: options.signal,
      });
    } catch (cause) {
      if (isAbortError(cause)) throw cause;
      throw ApiError.network(cause);
    }

    const parsed = await this.readBody(response);
    if (!response.ok) {
      throw ApiError.fromResponse(response.status, parsed.value);
    }
    if (!parsed.isJson) {
      throw ApiError.invalidResponse(
        "Response body was not valid JSON",
        parsed.value,
      );
    }
    return parsed.value;
  }

  private async readBody(
    response: Pick<Response, "headers" | "text">,
  ): Promise<{ isJson: boolean; value: unknown }> {
    const text = await response.text();
    if (text.length === 0) {
      return { isJson: false, value: null };
    }

    try {
      return { isJson: true, value: JSON.parse(text) as unknown };
    } catch {
      return { isJson: false, value: text };
    }
  }
}

export type Station = components["schemas"]["Station"];
export type RecommendationRequest =
  components["schemas"]["RecommendationRequest"];
export type RecommendationResult =
  components["schemas"]["RecommendationResult"];
export type PressureResponse = components["schemas"]["PressureResponse"];
export type PressureStation = components["schemas"]["PressureStation"];
export type SimulationRequest = components["schemas"]["SimulationRequest"];
export type SimulationResult = components["schemas"]["SimulationResult"];
export type Scenario = components["schemas"]["Scenario"];
export type Strategy = components["schemas"]["Strategy"];
export type DataType = components["schemas"]["DataType"];
export type Plan = components["schemas"]["Plan"];

export type ModelExplanation = components["schemas"]["ModelExplanation"];
export type WhatIfRequest = components["schemas"]["WhatIfRequest"];
export type WhatIfResult = components["schemas"]["WhatIfResult"];

export type RuntimeContext = components["schemas"]["RuntimeContext"];

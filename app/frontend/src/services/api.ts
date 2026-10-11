import type { components, operations } from "../types/api.generated";

import { ApiError, isAbortError, isRecord } from "./errors";

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

const DATA_TYPES = new Set(["mock", "simulated", "real", "mixed"]);

export class ApiClient {
  private readonly baseUrl: string;

  constructor(
    baseUrl: string,
    private readonly fetcher: typeof fetch = (...args) => fetch(...args),
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  listStations(signal?: AbortSignal): Promise<JsonResponse<"listStations">> {
    return this.request("/stations", { signal }).then((body) => {
      this.assertObject(body);
      this.assertDataType(body);
      if (!Array.isArray(body.stations)) {
        throw ApiError.invalidResponse("stations must be an array", body);
      }
      return body as JsonResponse<"listStations">;
    });
  }

  predict(
    body: JsonBody<"predictAvailability">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"predictAvailability">> {
    return this.request("/predict", { method: "POST", body, signal }).then(
      (response) => {
        this.assertObject(response);
        this.assertDataType(response);
        if (typeof response.station_id !== "string") {
          throw ApiError.invalidResponse(
            "predict requires station_id",
            response,
          );
        }
        return response as JsonResponse<"predictAvailability">;
      },
    );
  }

  recommend(
    body: JsonBody<"recommendStation">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"recommendStation">> {
    return this.request("/recommend", { method: "POST", body, signal }).then(
      (response) => {
        this.assertObject(response);
        this.assertDataType(response);
        if (typeof response.request_id !== "string") {
          throw ApiError.invalidResponse(
            "recommend requires request_id",
            response,
          );
        }
        return response as JsonResponse<"recommendStation">;
      },
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
    return this.request(`/pressure?${params}`, { signal }).then((response) => {
      this.assertObject(response);
      if (!Array.isArray(response.stations)) {
        throw ApiError.invalidResponse("pressure requires stations", response);
      }
      if (typeof response.scenario !== "string") {
        throw ApiError.invalidResponse("pressure requires scenario", response);
      }
      return response as JsonResponse<"getPressure">;
    });
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
      (response) => {
        this.assertObject(response);
        if (typeof response.strategy !== "string") {
          throw ApiError.invalidResponse(
            "simulate requires strategy",
            response,
          );
        }
        if (!isRecord(response.metrics)) {
          throw ApiError.invalidResponse("simulate requires metrics", response);
        }
        return response as JsonResponse<"simulate">;
      },
    );
  }

  reset(
    body: JsonBody<"resetDemo">,
    signal?: AbortSignal,
  ): Promise<JsonResponse<"resetDemo">> {
    return this.request("/reset", { method: "POST", body, signal }).then(
      (response) => {
        this.assertObject(response);
        if (typeof response.reset !== "boolean") {
          throw ApiError.invalidResponse("reset requires reset flag", response);
        }
        return response as JsonResponse<"resetDemo">;
      },
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

  private assertObject(body: unknown): asserts body is Record<string, unknown> {
    if (!isRecord(body)) {
      throw ApiError.invalidResponse("API response must be an object", body);
    }
  }

  private assertDataType(body: Record<string, unknown>): void {
    if (typeof body.data_type !== "string" || !DATA_TYPES.has(body.data_type)) {
      throw ApiError.invalidResponse("response requires data_type", body);
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

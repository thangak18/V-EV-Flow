import type { components, operations } from "../types/api.generated";

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

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiErrorBody = {
  code: string;
  message: string;
  details: unknown;
};

export class ApiClient {
  private readonly baseUrl: string;

  constructor(
    baseUrl: string,
    private readonly fetcher: typeof fetch = (...args) => fetch(...args),
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  listStations(signal?: AbortSignal): Promise<JsonResponse<"listStations">> {
    return this.request("/stations", { signal });
  }

  predict(
    body: JsonBody<"predictAvailability">,
  ): Promise<JsonResponse<"predictAvailability">> {
    return this.request("/predict", { method: "POST", body });
  }

  recommend(
    body: JsonBody<"recommendStation">,
  ): Promise<JsonResponse<"recommendStation">> {
    return this.request("/recommend", { method: "POST", body });
  }

  pressure(
    query: operations["getPressure"]["parameters"]["query"],
  ): Promise<JsonResponse<"getPressure">> {
    const params = new URLSearchParams({
      scenario: query.scenario,
      time: query.time,
    });
    return this.request(`/pressure?${params}`);
  }

  simulate(body: JsonBody<"simulate">): Promise<JsonResponse<"simulate">> {
    return this.request("/simulate", { method: "POST", body });
  }

  reset(body: JsonBody<"resetDemo">): Promise<JsonResponse<"resetDemo">> {
    return this.request("/reset", { method: "POST", body });
  }

  private async request<T>(
    path: string,
    options: { method?: "POST"; body?: unknown; signal?: AbortSignal } = {},
  ): Promise<T> {
    const response = await this.fetcher(`${this.baseUrl}${path}`, {
      method: options.method,
      headers:
        options.body === undefined
          ? undefined
          : { "Content-Type": "application/json" },
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
    const body = await this.readBody(response);

    if (!response.ok) {
      const error = this.normalizeError(response.status, body);
      throw new ApiError(
        error.status,
        error.code,
        error.message,
        error.details,
      );
    }

    if (!body.isJson) {
      throw new ApiError(
        response.status,
        "invalid_response",
        "Response body was not valid JSON",
        body.value,
      );
    }

    return body.value as T;
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

  private normalizeError(
    status: number,
    body: { isJson: boolean; value: unknown },
  ): ApiErrorBody & { status: number } {
    const value = body.isJson && isRecord(body.value) ? body.value : {};
    const fallbackMessage =
      typeof body.value === "string" && body.value.length > 0
        ? body.value
        : `Request failed with status ${status}`;

    return {
      status,
      code: typeof value.code === "string" ? value.code : "http_error",
      message:
        typeof value.message === "string" ? value.message : fallbackMessage,
      details: "details" in value ? value.details : null,
    };
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export type Station = components["schemas"]["Station"];

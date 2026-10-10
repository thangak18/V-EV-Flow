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
    public readonly body: unknown,
  ) {
    super(`API request failed with status ${status}`);
    this.name = "ApiError";
  }
}

export class ApiClient {
  private readonly baseUrl: string;

  constructor(
    baseUrl: string,
    private readonly fetcher: typeof fetch = fetch,
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  listStations(): Promise<JsonResponse<"listStations">> {
    return this.request("/stations");
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
    options: { method?: "POST"; body?: unknown } = {},
  ): Promise<T> {
    const response = await this.fetcher(`${this.baseUrl}${path}`, {
      method: options.method,
      headers:
        options.body === undefined
          ? undefined
          : { "Content-Type": "application/json" },
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    const body: unknown = await response.json();

    if (!response.ok) {
      throw new ApiError(response.status, body);
    }

    return body as T;
  }
}

export type Station = components["schemas"]["Station"];

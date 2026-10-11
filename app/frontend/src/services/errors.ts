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

  static fromResponse(status: number, body: unknown): ApiError {
    if (isRecord(body)) {
      if (typeof body.code === "string" && typeof body.message === "string") {
        return new ApiError(
          status,
          body.code,
          body.message,
          "details" in body ? body.details : null,
        );
      }

      if (Array.isArray(body.detail)) {
        return new ApiError(
          status,
          "VALIDATION_ERROR",
          "Request failed validation",
          body.detail,
        );
      }
    }

    if (typeof body === "string" && body.length > 0) {
      return new ApiError(status, "http_error", body, null);
    }

    return new ApiError(
      status,
      "http_error",
      `Request failed with status ${status}`,
      null,
    );
  }

  static network(cause: unknown): ApiError {
    const message =
      cause instanceof Error ? cause.message : "Network request failed";
    return new ApiError(0, "NETWORK_ERROR", message, cause);
  }

  static invalidResponse(message: string, details: unknown = null): ApiError {
    return new ApiError(502, "INVALID_API_RESPONSE", message, details);
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (error instanceof Error && error.name === "AbortError")
  );
}

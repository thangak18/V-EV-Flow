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
          formatValidationDetails(body.detail),
          body.detail,
        );
      }

      // FastAPI HTTPException(422, "…") → {"detail": "<string>"} (C8 time buckets).
      if (typeof body.detail === "string" && body.detail.length > 0) {
        return new ApiError(status, "VALIDATION_ERROR", body.detail, null);
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

export function formatValidationDetails(detail: unknown[]): string {
  const parts = detail
    .map((item) => {
      if (!isRecord(item)) return null;
      const loc = Array.isArray(item.loc)
        ? item.loc.filter((part) => part !== "body").join(".")
        : "";
      const msg = typeof item.msg === "string" ? item.msg : "invalid";
      return loc ? `${loc}: ${msg}` : msg;
    })
    .filter((part): part is string => Boolean(part));

  if (parts.length === 0) return "Request failed validation";
  return parts.join("; ");
}

/**
 * Observation/pressure times for C8+: aware +07:00 on a five-minute grid
 * (seconds and fractional seconds must be zero).
 */
export function isPlus07FiveMinuteBucket(value: string): boolean {
  const match =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?([+-]\d{2}:\d{2})$/.exec(
      value,
    );
  if (!match) return false;
  if (match[7] !== undefined) return false;
  if (match[8] !== "+07:00") return false;
  const minute = Number(match[5]);
  const second = Number(match[6]);
  if (second !== 0 || minute % 5 !== 0) return false;
  return isTimezoneAwareIso(value);
}

/**
 * ISO-8601 datetime with explicit timezone (Z or ±HH:MM).
 * Rejects non-existent calendar dates (e.g. 2026-02-31) that Date.parse
 * would silently normalize — matching backend Pydantic validation.
 */
export function isTimezoneAwareIso(value: string): boolean {
  const match =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$/.exec(
      value,
    );
  if (!match) return false;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const offset = match[7]!;

  if (month < 1 || month > 12) return false;
  if (hour > 23 || minute > 59 || second > 59) return false;

  if (offset !== "Z") {
    const offsetMatch = /^([+-])(\d{2}):(\d{2})$/.exec(offset);
    if (!offsetMatch) return false;
    const offsetHour = Number(offsetMatch[2]);
    const offsetMinute = Number(offsetMatch[3]);
    if (offsetHour > 14 || offsetMinute > 59) return false;
    if (offsetHour === 14 && offsetMinute !== 0) return false;
  }

  // Day 0 of next month → last valid day of `month` (UTC, leap-year aware).
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  if (day < 1 || day > daysInMonth) return false;

  return !Number.isNaN(Date.parse(value));
}

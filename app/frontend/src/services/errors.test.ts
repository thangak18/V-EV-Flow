import { describe, expect, test } from "vitest";

import {
  ApiError,
  isPlus07FiveMinuteBucket,
  isTimezoneAwareIso,
} from "./errors";
import { PressureResponseSchema } from "./schemas";

describe("isTimezoneAwareIso", () => {
  test("accepts timezone-aware real calendar dates", () => {
    expect(isTimezoneAwareIso("2026-10-13T16:00:00+07:00")).toBe(true);
    expect(isTimezoneAwareIso("2026-02-28T16:00:00Z")).toBe(true);
    expect(isTimezoneAwareIso("2024-02-29T00:00:00+00:00")).toBe(true);
  });

  test("rejects naive timestamps and impossible calendar days", () => {
    expect(isTimezoneAwareIso("2026-10-13T16:00:00")).toBe(false);
    expect(isTimezoneAwareIso("2026-02-31T16:00:00+07:00")).toBe(false);
    expect(isTimezoneAwareIso("2026-02-30T16:00:00+07:00")).toBe(false);
    expect(isTimezoneAwareIso("2026-04-31T12:00:00Z")).toBe(false);
    expect(isTimezoneAwareIso("2025-02-29T00:00:00Z")).toBe(false);
  });
});

describe("isPlus07FiveMinuteBucket", () => {
  test("accepts C8 observation and pressure buckets", () => {
    expect(isPlus07FiveMinuteBucket("2026-10-13T16:00:00+07:00")).toBe(true);
    expect(isPlus07FiveMinuteBucket("2026-10-13T16:05:00+07:00")).toBe(true);
  });

  test("rejects non-+07 offsets and off-grid minutes", () => {
    expect(isPlus07FiveMinuteBucket("2026-10-13T16:00:00Z")).toBe(false);
    expect(isPlus07FiveMinuteBucket("2026-10-13T16:01:00+07:00")).toBe(false);
    expect(isPlus07FiveMinuteBucket("2026-10-13T16:00:01+07:00")).toBe(false);
    expect(isPlus07FiveMinuteBucket("2026-10-13T16:00:00.000+07:00")).toBe(
      false,
    );
  });
});

describe("ApiError.fromResponse", () => {
  test("surfaces FastAPI string detail messages", () => {
    const error = ApiError.fromResponse(422, {
      detail: "timestamps must use the +07:00 convention",
    });
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.message).toBe("timestamps must use the +07:00 convention");
  });
});

describe("PressureResponseSchema calendar validation", () => {
  test("rejects Feb 31 that Date.parse would normalize", () => {
    const parsed = PressureResponseSchema.safeParse({
      time: "2026-02-31T16:00:00+07:00",
      scenario: "normal",
      stations: [],
      contract_version: "0.1.0",
    });
    expect(parsed.success).toBe(false);
  });
});

import { describe, expect, test } from "vitest";

import { PRESSURE_COLORS, pressureColor } from "./pressureColors";

describe("pressureColor", () => {
  test("maps score bands to shared palette tokens", () => {
    expect(pressureColor(0.1)).toBe(PRESSURE_COLORS.low);
    expect(pressureColor(0.33)).toBe(PRESSURE_COLORS.mid);
    expect(pressureColor(0.66)).toBe(PRESSURE_COLORS.high);
    expect(PRESSURE_COLORS).toEqual({
      low: "#1f7a5c",
      mid: "#c27803",
      high: "#c23b22",
    });
  });
});

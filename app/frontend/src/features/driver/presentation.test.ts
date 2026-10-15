import { expect, test } from "vitest";
import { displayDistance, displayReason } from "./presentation";

test("translates backend feasibility explanations and preserves new reasons", () => {
  expect(displayReason("Arrival SOC was insufficient.")).toBe(
    "Pin khi đến trạm thấp hơn mức dự phòng cho phép.",
  );
  expect(displayReason("Unrecognized producer explanation")).toBe(
    "Unrecognized producer explanation",
  );
});

test("preserves small nonzero road distances", () => {
  expect(displayDistance(1.062)).toBe("1,1");
  expect(displayDistance(0.358)).toBe("0,4");
  expect(displayDistance(0.03)).toBe("<0,1");
  expect(displayDistance(0)).toBe("0");
  expect(displayDistance(15)).toBe("15");
});

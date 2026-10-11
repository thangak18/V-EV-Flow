import { describe, expect, test } from "vitest";

import { isNumericDraft, parseLocaleNumber } from "./numberField";

describe("isNumericDraft", () => {
  test("allows empty and in-progress decimal separators", () => {
    expect(isNumericDraft("")).toBe(true);
    expect(isNumericDraft("30")).toBe(true);
    expect(isNumericDraft("30.")).toBe(true);
    expect(isNumericDraft("30,")).toBe(true);
    expect(isNumericDraft("0.18")).toBe(true);
    expect(isNumericDraft("0,18")).toBe(true);
    expect(isNumericDraft(".5")).toBe(true);
    expect(isNumericDraft(",5")).toBe(true);
  });

  test("rejects letters and multiple separators", () => {
    expect(isNumericDraft("abc")).toBe(false);
    expect(isNumericDraft("1.2.3")).toBe(false);
    expect(isNumericDraft("1,2,3")).toBe(false);
    expect(isNumericDraft("1.2,3")).toBe(false);
  });
});

describe("parseLocaleNumber", () => {
  test("parses dot and comma decimals to the same value", () => {
    expect(parseLocaleNumber("0.18")).toBe(0.18);
    expect(parseLocaleNumber("0,18")).toBe(0.18);
    expect(parseLocaleNumber("30.5")).toBe(30.5);
    expect(parseLocaleNumber("30,5")).toBe(30.5);
    expect(parseLocaleNumber(" 42 ")).toBe(42);
  });

  test("returns null for empty or incomplete drafts instead of 0", () => {
    expect(parseLocaleNumber("")).toBeNull();
    expect(parseLocaleNumber("   ")).toBeNull();
    expect(parseLocaleNumber("30.")).toBeNull();
    expect(parseLocaleNumber("30,")).toBeNull();
    expect(parseLocaleNumber(".")).toBeNull();
    expect(parseLocaleNumber(",")).toBeNull();
  });
});

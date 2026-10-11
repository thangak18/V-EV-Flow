/**
 * Draft-friendly numeric text helpers for Driver vehicle fields.
 * Keeps intermediate input (empty, trailing separator) without coercing to 0.
 */

const DRAFT_PATTERN = /^-?\d*([.,]\d*)?$/;

/** True for empty or in-progress numeric typing (supports `.` and `,`). */
export function isNumericDraft(raw: string): boolean {
  return DRAFT_PATTERN.test(raw.trim());
}

/**
 * Parse a finished locale number. Returns null for empty / incomplete drafts
 * (e.g. "", "30.", ",", ".") so callers can block submit instead of treating
 * them as 0.
 */
export function parseLocaleNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (trimmed.length === 0) return null;

  const normalized = trimmed.replace(",", ".");
  if (
    normalized === "." ||
    normalized === "-" ||
    normalized === "-." ||
    normalized.endsWith(".")
  ) {
    return null;
  }
  if (!/^-?(?:\d+(\.\d+)?|\.\d+)$/.test(normalized)) return null;

  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

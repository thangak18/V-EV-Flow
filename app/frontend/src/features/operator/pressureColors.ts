/** Shared with CSS `--pressure-*` tokens in index.css. */
export const PRESSURE_COLORS = {
  low: "#1f7a5c",
  mid: "#c27803",
  high: "#c23b22",
} as const;

export function pressureColor(score: number): string {
  if (score >= 0.66) return PRESSURE_COLORS.high;
  if (score >= 0.33) return PRESSURE_COLORS.mid;
  return PRESSURE_COLORS.low;
}

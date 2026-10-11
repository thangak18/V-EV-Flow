export const CORRIDOR_PRESETS = {
  hcm_vt: {
    id: "hcm_vt",
    label: "TP.HCM → Vũng Tàu",
    origin: { lat: 10.78, lng: 106.7 },
    destination: { lat: 10.35, lng: 107.08 },
  },
  vt_hcm: {
    id: "vt_hcm",
    label: "Vũng Tàu → TP.HCM",
    origin: { lat: 10.35, lng: 107.08 },
    destination: { lat: 10.78, lng: 106.7 },
  },
} as const;

export type CorridorPresetId = keyof typeof CORRIDOR_PRESETS;

export const DEFAULT_DEMO_TIME = "2026-10-13T16:00:00+07:00";

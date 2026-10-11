import { useMemo, useState } from "react";

import type { RecommendationRequest, Scenario } from "../../services/api";
import { isTimezoneAwareIso } from "../../services/errors";
import {
  CORRIDOR_PRESETS,
  DEFAULT_DEMO_TIME,
  type CorridorPresetId,
} from "./corridorPresets";

type Props = {
  pending: boolean;
  presetId: CorridorPresetId;
  onPresetChange: (presetId: CorridorPresetId) => void;
  onSubmit: (request: RecommendationRequest) => void;
};

function samePayload(
  left: Omit<RecommendationRequest, "request_id">,
  right: Omit<RecommendationRequest, "request_id">,
): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function DriverForm({
  pending,
  presetId,
  onPresetChange,
  onSubmit,
}: Props) {
  const [socPct, setSocPct] = useState(20);
  const [batteryKwh, setBatteryKwh] = useState(60);
  const [consumption, setConsumption] = useState(0.18);
  const [connector, setConnector] = useState("CCS2");
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [demoTime, setDemoTime] = useState(DEFAULT_DEMO_TIME);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [lastPayload, setLastPayload] = useState<Omit<
    RecommendationRequest,
    "request_id"
  > | null>(null);

  const timeInvalid = !isTimezoneAwareIso(demoTime);
  const invalid = useMemo(() => {
    return (
      timeInvalid ||
      socPct < 0 ||
      socPct > 100 ||
      batteryKwh <= 0 ||
      consumption <= 0 ||
      connector.trim().length === 0
    );
  }, [timeInvalid, socPct, batteryKwh, consumption, connector]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (pending || invalid) return;

    const preset = CORRIDOR_PRESETS[presetId];
    const payload: Omit<RecommendationRequest, "request_id"> = {
      origin: preset.origin,
      destination: preset.destination,
      observed_at: demoTime,
      depart_time: demoTime,
      scenario,
      vehicle: {
        soc_pct: socPct,
        battery_kwh: batteryKwh,
        consumption_kwh_per_km: consumption,
        connector_type: connector,
      },
    };

    const nextId =
      lastPayload && samePayload(lastPayload, payload)
        ? requestId
        : crypto.randomUUID();
    setRequestId(nextId);
    setLastPayload(payload);
    onSubmit({ ...payload, request_id: nextId });
  }

  return (
    <form className="driver-form" onSubmit={handleSubmit} noValidate>
      <fieldset>
        <legend>Corridor preset</legend>
        <label>
          Route
          <select
            value={presetId}
            onChange={(event) =>
              onPresetChange(event.target.value as CorridorPresetId)
            }
          >
            {Object.values(CORRIDOR_PRESETS).map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Scenario
          <select
            value={scenario}
            onChange={(event) => setScenario(event.target.value as Scenario)}
          >
            <option value="normal">Normal day</option>
            <option value="holiday_30_4">30/4 holiday</option>
            <option value="tet">Tết</option>
          </select>
        </label>
        <label>
          Demo time (+07:00)
          <input
            type="text"
            value={demoTime}
            onChange={(event) => setDemoTime(event.target.value)}
            aria-invalid={timeInvalid}
          />
        </label>
      </fieldset>

      <fieldset>
        <legend>Vehicle</legend>
        <label>
          SOC %
          <input
            type="number"
            min={0}
            max={100}
            value={socPct}
            onChange={(event) => setSocPct(Number(event.target.value))}
          />
        </label>
        <label>
          Battery kWh
          <input
            type="number"
            min={1}
            step={1}
            value={batteryKwh}
            onChange={(event) => setBatteryKwh(Number(event.target.value))}
          />
        </label>
        <label>
          Consumption kWh/km
          <input
            type="number"
            min={0.01}
            step={0.01}
            value={consumption}
            onChange={(event) => setConsumption(Number(event.target.value))}
          />
        </label>
        <label>
          Connector
          <input
            type="text"
            value={connector}
            onChange={(event) => setConnector(event.target.value)}
          />
        </label>
      </fieldset>

      {invalid ? (
        <p className="field-error" role="alert">
          {timeInvalid
            ? "Demo time must be ISO-8601 with timezone (e.g. 2026-10-13T16:00:00+07:00)."
            : "Check SOC (0–100), battery > 0, consumption > 0, and connector."}
        </p>
      ) : null}

      <button type="submit" disabled={pending || invalid}>
        {pending ? "Finding plan…" : "Tìm kế hoạch sạc"}
      </button>
    </form>
  );
}

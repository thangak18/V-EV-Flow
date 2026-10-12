import { useMemo, useState } from "react";

import type { RecommendationRequest, Scenario } from "../../services/api";
import { isTimezoneAwareIso } from "../../services/errors";
import {
  CORRIDOR_PRESETS,
  DEFAULT_DEMO_TIME,
  type CorridorPresetId,
} from "./corridorPresets";
import { isNumericDraft, parseLocaleNumber } from "./numberField";

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

function onDraftNumberChange(
  setter: (value: string) => void,
): (event: React.ChangeEvent<HTMLInputElement>) => void {
  return (event) => {
    const next = event.target.value;
    if (isNumericDraft(next)) setter(next);
  };
}

export function DriverForm({
  pending,
  presetId,
  onPresetChange,
  onSubmit,
}: Props) {
  const [socPct, setSocPct] = useState("20");
  const [batteryKwh, setBatteryKwh] = useState("60");
  const [consumption, setConsumption] = useState("0.18");
  const [connector, setConnector] = useState("CCS2");
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [demoTime, setDemoTime] = useState(DEFAULT_DEMO_TIME);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [lastPayload, setLastPayload] = useState<Omit<
    RecommendationRequest,
    "request_id"
  > | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const parsedSoc = parseLocaleNumber(socPct);
  const parsedBattery = parseLocaleNumber(batteryKwh);
  const parsedConsumption = parseLocaleNumber(consumption);

  const timeInvalid = !isTimezoneAwareIso(demoTime);
  const socInvalid = parsedSoc === null || parsedSoc < 0 || parsedSoc > 100;
  const batteryInvalid = parsedBattery === null || parsedBattery <= 0;
  const consumptionInvalid =
    parsedConsumption === null || parsedConsumption <= 0;
  const connectorInvalid = connector.trim().length === 0;
  const advancedInvalid = timeInvalid || batteryInvalid || consumptionInvalid;
  const detailsOpen = advancedOpen || advancedInvalid;

  const invalid = useMemo(() => {
    return (
      timeInvalid ||
      socInvalid ||
      batteryInvalid ||
      consumptionInvalid ||
      connectorInvalid
    );
  }, [
    timeInvalid,
    socInvalid,
    batteryInvalid,
    consumptionInvalid,
    connectorInvalid,
  ]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (
      pending ||
      invalid ||
      parsedSoc === null ||
      parsedBattery === null ||
      parsedConsumption === null
    ) {
      return;
    }

    const preset = CORRIDOR_PRESETS[presetId];
    const payload: Omit<RecommendationRequest, "request_id"> = {
      origin: preset.origin,
      destination: preset.destination,
      observed_at: demoTime,
      depart_time: demoTime,
      scenario,
      vehicle: {
        soc_pct: parsedSoc,
        battery_kwh: parsedBattery,
        consumption_kwh_per_km: parsedConsumption,
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
      <div className="driver-primary-fields">
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
        <div className="driver-primary-row">
          <label>
            SOC %
            <input
              type="text"
              inputMode="decimal"
              value={socPct}
              onChange={onDraftNumberChange(setSocPct)}
              aria-invalid={socInvalid}
            />
          </label>
          <label>
            Connector
            <input
              type="text"
              value={connector}
              onChange={(event) => setConnector(event.target.value)}
              aria-invalid={connectorInvalid}
            />
          </label>
        </div>
      </div>

      <details
        className="driver-advanced"
        open={detailsOpen}
        onToggle={(event) => {
          const next = event.currentTarget.open;
          // Keep advanced open while its fields are invalid so errors stay visible.
          if (advancedInvalid && !next) {
            setAdvancedOpen(true);
            return;
          }
          setAdvancedOpen(next);
        }}
      >
        <summary>Battery, consumption &amp; demo time</summary>
        <div className="driver-advanced-fields">
          <label>
            Battery kWh
            <input
              type="text"
              inputMode="decimal"
              value={batteryKwh}
              onChange={onDraftNumberChange(setBatteryKwh)}
              aria-invalid={batteryInvalid}
            />
          </label>
          <label>
            Consumption kWh/km
            <input
              type="text"
              inputMode="decimal"
              value={consumption}
              onChange={onDraftNumberChange(setConsumption)}
              aria-invalid={consumptionInvalid}
            />
          </label>
          <label>
            Demo time (+07:00)
            <input
              className="input-datetime"
              type="text"
              value={demoTime}
              onChange={(event) => setDemoTime(event.target.value)}
              aria-invalid={timeInvalid}
              autoComplete="off"
              spellCheck={false}
            />
          </label>
        </div>
      </details>

      {invalid ? (
        <p className="field-error" role="alert">
          {timeInvalid
            ? "Demo time must be ISO-8601 with timezone (e.g. 2026-10-13T16:00:00+07:00)."
            : "Check SOC (0–100), battery > 0, consumption > 0, and connector. Empty numeric fields are not allowed."}
        </p>
      ) : null}

      <button type="submit" disabled={pending || invalid}>
        {pending ? "Finding plan…" : "Tìm kế hoạch sạc"}
      </button>
    </form>
  );
}

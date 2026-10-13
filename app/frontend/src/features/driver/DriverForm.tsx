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
  // Stay open while invalid; field edits also sticky-open so mid-typing
  // (e.g. "0,1" → valid) does not collapse and remount inputs.
  const detailsOpen = advancedInvalid || advancedOpen;

  function touchAdvanced() {
    setAdvancedOpen(true);
  }

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
          Hành lang
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
          Kịch bản
          <select
            value={scenario}
            onChange={(event) => setScenario(event.target.value as Scenario)}
          >
            <option value="normal">Ngày thường</option>
            <option value="holiday_30_4">Lễ 30/4</option>
            <option value="tet">Tết</option>
          </select>
        </label>
        <div className="driver-primary-row">
          <label>
            Pin hiện tại (SOC %)
            <input
              type="text"
              inputMode="decimal"
              value={socPct}
              onChange={onDraftNumberChange(setSocPct)}
              aria-invalid={socInvalid}
            />
          </label>
          <label>
            Đầu cắm
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
        className={
          advancedInvalid
            ? "driver-advanced driver-advanced--locked"
            : "driver-advanced"
        }
        open={detailsOpen}
        onToggle={(event) => {
          if (advancedInvalid) {
            // Ignore collapse attempts while Advanced fields are invalid.
            event.currentTarget.open = true;
            setAdvancedOpen(true);
            return;
          }
          setAdvancedOpen(event.currentTarget.open);
        }}
      >
        <summary
          aria-disabled={advancedInvalid || undefined}
          onClick={(event) => {
            if (advancedInvalid) {
              event.preventDefault();
              event.stopPropagation();
            }
          }}
        >
          Pin xe, tiêu hao &amp; giờ demo
        </summary>
        <div className="driver-advanced-fields">
          <label>
            Dung lượng pin (kWh)
            <input
              type="text"
              inputMode="decimal"
              value={batteryKwh}
              onChange={(event) => {
                touchAdvanced();
                onDraftNumberChange(setBatteryKwh)(event);
              }}
              aria-invalid={batteryInvalid}
            />
          </label>
          <label>
            Tiêu hao (kWh/km)
            <input
              type="text"
              inputMode="decimal"
              value={consumption}
              onChange={(event) => {
                touchAdvanced();
                onDraftNumberChange(setConsumption)(event);
              }}
              aria-invalid={consumptionInvalid}
            />
          </label>
          <label>
            Giờ demo (+07:00)
            <input
              className="input-datetime"
              type="text"
              value={demoTime}
              onChange={(event) => {
                touchAdvanced();
                setDemoTime(event.target.value);
              }}
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
            ? "Giờ demo phải là ISO-8601 có múi giờ (ví dụ 2026-10-13T16:00:00+07:00)."
            : "Kiểm tra SOC (0–100), dung lượng pin > 0, tiêu hao > 0 và đầu cắm. Không để trống số."}
        </p>
      ) : null}

      <button type="submit" disabled={pending || invalid}>
        {pending ? "Đang tìm…" : "Tìm kế hoạch sạc"}
      </button>
    </form>
  );
}

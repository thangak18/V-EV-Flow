import { useMemo, useState } from "react";

import type {
  RecommendationRequest,
  Scenario,
  RuntimeContext,
} from "../../services/api";
import { isPlus07FiveMinuteBucket } from "../../services/errors";
import {
  DEFAULT_ORIGIN,
  DEFAULT_DESTINATION,
  DEFAULT_DEMO_TIME,
  type TripLocation,
} from "./corridorPresets";
import { PlaceSearch } from "./PlaceSearch";
import { isNumericDraft, parseLocaleNumber } from "./numberField";

type Props = {
  pending: boolean;
  locations?: TripLocation[];
  origin?: string;
  destination?: string;
  onLocationChange?: (field: "origin" | "destination", value: string) => void;
  runtime?: RuntimeContext;
  runtimeError?: string;
  runtimeLoading?: boolean;
  onScenarioChange?: (scenario: Scenario) => void;
  onResolveLocation?: (
    field: "origin" | "destination",
    location: TripLocation,
  ) => void;
  resolvedOrigin?: TripLocation;
  resolvedDestination?: TripLocation;
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
  locations = [DEFAULT_ORIGIN, DEFAULT_DESTINATION],
  origin = DEFAULT_ORIGIN.label,
  destination = DEFAULT_DESTINATION.label,
  onLocationChange,
  runtime,
  runtimeError,
  runtimeLoading,
  onScenarioChange,
  onResolveLocation,
  resolvedOrigin,
  resolvedDestination,
  onSubmit,
}: Props) {
  const [socPct, setSocPct] = useState("20");
  const [batteryKwh, setBatteryKwh] = useState("60");
  const [consumption, setConsumption] = useState("0.18");
  const [connector, setConnector] = useState("CCS2");
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [demoTimeDraft, setDemoTime] = useState<string | null>(null);
  const demoTime = demoTimeDraft ?? runtime?.observed_at ?? DEFAULT_DEMO_TIME;
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [lastPayload, setLastPayload] = useState<Omit<
    RecommendationRequest,
    "request_id"
  > | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const parsedSoc = parseLocaleNumber(socPct);
  const parsedBattery = parseLocaleNumber(batteryKwh);
  const parsedConsumption = parseLocaleNumber(consumption);

  const selectedOrigin =
    (resolvedOrigin?.label === origin ? resolvedOrigin : undefined) ??
    locations.find((location) => location.label === origin);
  const selectedDestination =
    (resolvedDestination?.label === destination
      ? resolvedDestination
      : undefined) ??
    locations.find((location) => location.label === destination);
  const routeInvalid =
    !selectedOrigin ||
    !selectedDestination ||
    (selectedOrigin.lat === selectedDestination.lat &&
      selectedOrigin.lng === selectedDestination.lng);
  const timeInvalid = !isPlus07FiveMinuteBucket(demoTime);
  const socInvalid = parsedSoc === null || parsedSoc < 0 || parsedSoc > 100;
  const batteryInvalid = parsedBattery === null || parsedBattery <= 0;
  const consumptionInvalid =
    parsedConsumption === null || parsedConsumption <= 0;
  const connectorInvalid = connector.trim().length === 0;
  const advancedInvalid = timeInvalid || batteryInvalid || consumptionInvalid;
  const detailsOpen = advancedInvalid || advancedOpen;

  function touchAdvanced() {
    setAdvancedOpen(true);
  }

  const invalid = useMemo(() => {
    return (
      routeInvalid ||
      timeInvalid ||
      socInvalid ||
      batteryInvalid ||
      consumptionInvalid ||
      connectorInvalid
    );
  }, [
    routeInvalid,
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
      !selectedOrigin ||
      !selectedDestination ||
      parsedSoc === null ||
      parsedBattery === null ||
      parsedConsumption === null
    ) {
      return;
    }

    const payload: Omit<RecommendationRequest, "request_id"> = {
      origin: { lat: selectedOrigin.lat, lng: selectedOrigin.lng },
      destination: {
        lat: selectedDestination.lat,
        lng: selectedDestination.lng,
      },
      observed_at: demoTime,
      // Live observation may lag the click by a few minutes. Keep that source
      // timestamp for features, but depart now instead of replaying a past trip.
      depart_time:
        runtime?.clock_mode === "live"
          ? new Date(Date.now() + 7 * 60 * 60 * 1000)
              .toISOString()
              .replace("Z", "+07:00")
          : demoTime,
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
    <form className="driver-toolbar" onSubmit={handleSubmit} noValidate>
      <div className="driver-toolbar__fields">
        {(["origin", "destination"] as const).map((field) => (
          <PlaceSearch
            key={field}
            label={field === "origin" ? "Điểm đi" : "Điểm đến"}
            value={field === "origin" ? origin : destination}
            locations={locations}
            enabled={runtime?.places_available ?? false}
            disabled={runtimeLoading || !!runtimeError}
            resolved={field === "origin" ? resolvedOrigin : resolvedDestination}
            invalid={routeInvalid}
            onChange={(value) => onLocationChange?.(field, value)}
            onResolve={(location) => onResolveLocation?.(field, location)}
          />
        ))}
        <datalist id="trip-locations">
          {locations.map((location) => (
            <option key={location.label} value={location.label} />
          ))}
        </datalist>
        <label className="field-chip">
          <span className="field-chip__label">Kịch bản</span>
          <select
            value={scenario}
            onChange={(event) => {
              setScenario(event.target.value as Scenario);
              setDemoTime(null);
              onScenarioChange?.(event.target.value as Scenario);
            }}
          >
            <option value="normal">Ngày thường</option>
            <option value="holiday_30_4">Lễ 30/4</option>
            <option value="tet">Tết</option>
          </select>
        </label>
        <label className="field-chip">
          <span className="field-chip__label">Pin hiện tại (SOC %)</span>
          <input
            type="text"
            inputMode="decimal"
            value={socPct}
            onChange={onDraftNumberChange(setSocPct)}
            aria-invalid={socInvalid}
          />
        </label>
        <label className="field-chip">
          <span className="field-chip__label">Đầu cắm</span>
          <input
            type="text"
            value={connector}
            onChange={(event) => setConnector(event.target.value)}
            aria-invalid={connectorInvalid}
          />
        </label>
      </div>

      <div className="driver-toolbar__actions">
        <button
          type="submit"
          className="btn-primary"
          disabled={
            pending ||
            invalid ||
            runtimeLoading ||
            !!runtimeError ||
            runtime?.available === false
          }
        >
          {pending ? "Đang tìm…" : "Tìm kế hoạch sạc"}
        </button>

        <details
          className={
            advancedInvalid
              ? "driver-advanced driver-advanced--locked"
              : "driver-advanced"
          }
          open={detailsOpen}
          onToggle={(event) => {
            if (advancedInvalid) {
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
            Thông số xe
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
      </div>

      <p
        id="trip-location-help"
        className="status-message driver-toolbar__hint"
      >
        {runtime?.places_available
          ? "Tìm địa chỉ bằng Goong hoặc chọn địa điểm trong danh mục."
          : "Gõ rồi chọn địa điểm trong danh sách."}{" "}
        Dữ liệu trạm hiện phủ vùng demo TP.HCM–Vũng Tàu.
        {runtime
          ? ` ${runtime.message} Phạm vi dự báo tối đa ${runtime.max_horizon_minutes} phút.`
          : ""}
      </p>
      {runtimeError ? (
        <p className="field-error" role="alert">
          {runtimeError}
        </p>
      ) : null}
      {invalid ? (
        <p className="field-error driver-toolbar__error" role="alert">
          {routeInvalid
            ? "Chọn hai địa điểm khác nhau trong danh sách gợi ý."
            : timeInvalid
              ? "Giờ demo phải là +07:00, căn 5 phút (ví dụ 2026-10-13T16:00:00+07:00)."
              : "Kiểm tra SOC (0–100), dung lượng pin > 0, tiêu hao > 0 và đầu cắm. Không để trống số."}
        </p>
      ) : null}
    </form>
  );
}

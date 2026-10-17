import { useEffect, useMemo, useState } from "react";

import type {
  RecommendationRequest,
  Scenario,
  RuntimeContext,
} from "../../services/api";
import {
  isPlus07FiveMinuteBucket,
  isTimezoneAwareIso,
} from "../../services/errors";
import {
  DEFAULT_ORIGIN,
  DEFAULT_DESTINATION,
  DEFAULT_DEMO_TIME,
  type TripLocation,
} from "./corridorPresets";
import { PlaceSearch } from "./PlaceSearch";
import { VEHICLE_CONNECTORS } from "./connectorOptions";
import { isNumericDraft, parseLocaleNumber } from "./numberField";

type Props = {
  pending: boolean;
  connectorTypes?: string[];
  locations?: TripLocation[];
  origin?: string;
  destination?: string;
  onLocationChange?: (field: "origin" | "destination", value: string) => void;
  runtime?: RuntimeContext;
  runtimeError?: string;
  runtimeLoading?: boolean;
  onRetryRuntime?: () => void;
  onScenarioChange?: (scenario: Scenario) => void;
  onDepartureChange?: () => void;
  onResolveLocation?: (
    field: "origin" | "destination",
    location: TripLocation,
  ) => void;
  resolvedOrigin?: TripLocation;
  resolvedDestination?: TripLocation;
  onSubmit: (request: RecommendationRequest) => void;
};

function vietnamTime(timestamp: number): string {
  return new Date(timestamp + 7 * 60 * 60 * 1000)
    .toISOString()
    .replace("Z", "+07:00");
}

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
  connectorTypes = ["CCS2"],
  locations = [DEFAULT_ORIGIN, DEFAULT_DESTINATION],
  origin = DEFAULT_ORIGIN.label,
  destination = DEFAULT_DESTINATION.label,
  onLocationChange,
  runtime,
  runtimeError,
  runtimeLoading,
  onRetryRuntime,
  onScenarioChange,
  onDepartureChange,
  onResolveLocation,
  resolvedOrigin,
  resolvedDestination,
  onSubmit,
}: Props) {
  const [socPct, setSocPct] = useState("20");
  const [batteryKwh, setBatteryKwh] = useState("60");
  const [consumption, setConsumption] = useState("0.18");
  const [connector, setConnector] = useState("CCS2");
  const supportedConnectors = [...new Set(connectorTypes)]
    .filter(Boolean)
    .sort();
  const connectorOptions = [
    ...VEHICLE_CONNECTORS,
    ...supportedConnectors
      .filter(
        (value) => !VEHICLE_CONNECTORS.some((option) => option.value === value),
      )
      .map((value) => ({ value, label: value })),
  ];
  const selectedConnector = connector;
  const [scenario, setScenario] = useState<Scenario>("normal");
  const observedAt = runtime ? (runtime.observed_at ?? "") : DEFAULT_DEMO_TIME;
  const [liveNow, setLiveNow] = useState(() => Date.now());
  const [departureDraft, setDepartureDraft] = useState<string | null>(null);
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
    (runtime?.places_available
      ? undefined
      : locations.find((location) => location.label === origin));
  const selectedDestination =
    (resolvedDestination?.label === destination
      ? resolvedDestination
      : undefined) ??
    (runtime?.places_available
      ? undefined
      : locations.find((location) => location.label === destination));
  const routeInvalid =
    !selectedOrigin ||
    !selectedDestination ||
    (selectedOrigin.lat === selectedDestination.lat &&
      selectedOrigin.lng === selectedDestination.lng);
  const timeInvalid = !isPlus07FiveMinuteBucket(observedAt);
  const live = runtime?.clock_mode === "live";
  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => setLiveNow(Date.now()), 30_000);
    return () => clearInterval(timer);
  }, [live]);
  const defaultDeparture = live
    ? vietnamTime(
        Math.max(
          liveNow,
          Number.isFinite(Date.parse(observedAt))
            ? Date.parse(observedAt)
            : liveNow,
        ),
      )
    : observedAt;
  const departureValue = departureDraft ?? defaultDeparture.slice(0, 16);
  const departureIso =
    departureDraft === null
      ? defaultDeparture
      : /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(departureDraft)
        ? `${departureDraft}:00+07:00`
        : "";
  const horizon = runtime?.max_horizon_minutes ?? 60;
  const forecastEnd = Date.parse(observedAt) + horizon * 60_000;
  const replay = runtime?.clock_mode === "replay";
  const historyStart = runtime?.history_start ?? "";
  const historyEnd = runtime?.history_end ?? "";
  const historyReady =
    isTimezoneAwareIso(historyStart) && isTimezoneAwareIso(historyEnd);
  const validDeparture = isTimezoneAwareIso(departureIso);
  const inHistory =
    historyReady &&
    validDeparture &&
    Date.parse(departureIso) >= Date.parse(historyStart) &&
    Date.parse(departureIso) <= Date.parse(historyEnd);
  // Replay reads an actual historical snapshot, not an extrapolated forecast
  // from the default 16:00 clock. Live mode keeps its latest observed snapshot.
  const selectedObservation =
    replay && departureDraft !== null && inHistory
      ? vietnamTime(
          Math.floor(Date.parse(departureIso) / 300_000) * 300_000,
        ).replace(".000+", "+")
      : observedAt;
  const departureError = !validDeparture
    ? "Chọn ngày và giờ khởi hành hợp lệ."
    : replay && departureDraft !== null
      ? !historyReady
        ? "Chưa lấy được khoảng dữ liệu lịch sử để chọn giờ khởi hành. Hãy dùng lại mốc dữ liệu hoặc thử kết nối lại."
        : !inHistory
          ? "Giờ khởi hành nằm ngoài khoảng dữ liệu mô phỏng hiện có. Chọn ngày giờ trong khoảng lịch sử được hiển thị."
          : ""
      : Date.parse(departureIso) < Date.parse(observedAt)
        ? "Giờ khởi hành không được sớm hơn mốc dữ liệu đang xem."
        : Date.parse(departureIso) >= forecastEnd
          ? "Giờ khởi hành quá xa mốc dữ liệu mới nhất. Cần dữ liệu cập nhật để dự báo chuyến đi này."
          : "";
  const departureInvalid = !!departureError;
  const socInvalid = parsedSoc === null || parsedSoc < 0 || parsedSoc > 100;
  const batteryInvalid = parsedBattery === null || parsedBattery <= 0;
  const consumptionInvalid =
    parsedConsumption === null || parsedConsumption <= 0;
  const connectorInvalid = !supportedConnectors.includes(selectedConnector);
  const advancedInvalid = batteryInvalid || consumptionInvalid;
  const detailsOpen = advancedInvalid || advancedOpen;

  function touchAdvanced() {
    setAdvancedOpen(true);
  }

  const invalid = useMemo(() => {
    return (
      routeInvalid ||
      timeInvalid ||
      departureInvalid ||
      socInvalid ||
      batteryInvalid ||
      consumptionInvalid ||
      connectorInvalid
    );
  }, [
    routeInvalid,
    timeInvalid,
    departureInvalid,
    socInvalid,
    batteryInvalid,
    consumptionInvalid,
    connectorInvalid,
  ]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (
      pending ||
      runtimeLoading ||
      !!runtimeError ||
      runtime?.available === false ||
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
      observed_at: selectedObservation,
      // Use the actual replay snapshot, or the latest live observation.
      depart_time:
        departureDraft === null && live
          ? vietnamTime(Date.now())
          : departureIso,
      scenario,
      vehicle: {
        soc_pct: parsedSoc,
        battery_kwh: parsedBattery,
        consumption_kwh_per_km: parsedConsumption,
        connector_type: selectedConnector,
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
            invalid={
              field === "origin"
                ? !selectedOrigin ||
                  !!(
                    selectedDestination &&
                    selectedOrigin.lat === selectedDestination.lat &&
                    selectedOrigin.lng === selectedDestination.lng
                  )
                : !selectedDestination ||
                  !!(
                    selectedOrigin &&
                    selectedOrigin.lat === selectedDestination.lat &&
                    selectedOrigin.lng === selectedDestination.lng
                  )
            }
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
          <span className="field-chip__label">Kịch bản nhu cầu sạc</span>
          <select
            value={scenario}
            onChange={(event) => {
              const next = event.target.value as Scenario;
              if (next === scenario) return;
              setDepartureDraft(null);
              setScenario(next);
              onScenarioChange?.(next);
            }}
          >
            <option value="normal">Ngày thường</option>
            <option value="holiday_30_4">Lễ 30/4</option>
            <option value="tet">Tết</option>
          </select>
        </label>
        <div className="field-chip driver-departure">
          <label htmlFor="driver-departure" className="field-chip__label">
            Giờ khởi hành
          </label>
          <input
            id="driver-departure"
            type="datetime-local"
            step={60}
            value={departureValue}
            min={
              replay && historyReady
                ? vietnamTime(Date.parse(historyStart)).slice(0, 16)
                : !timeInvalid
                  ? observedAt.slice(0, 16)
                  : undefined
            }
            max={
              replay && historyReady
                ? vietnamTime(Date.parse(historyEnd)).slice(0, 16)
                : !timeInvalid
                  ? vietnamTime(forecastEnd - 60_000).slice(0, 16)
                  : undefined
            }
            disabled={runtimeLoading || !!runtimeError || timeInvalid}
            aria-invalid={departureInvalid}
            aria-describedby="driver-departure-help"
            onChange={(event) => {
              setDepartureDraft(event.target.value);
              onDepartureChange?.();
            }}
          />
        </div>
        <div className="field-chip">
          <label className="field-chip__label" htmlFor="driver-soc">
            Mức pin hiện tại (%)
          </label>
          <input
            id="driver-soc"
            type="text"
            inputMode="decimal"
            value={socPct}
            onChange={onDraftNumberChange(setSocPct)}
            aria-invalid={socInvalid}
            aria-describedby="driver-soc-help"
          />
          <small id="driver-soc-help">
            Nhập từ 0 đến 100% theo mức pin trên xe.
          </small>
        </div>
        <div className="field-chip">
          <label className="field-chip__label" htmlFor="driver-connector">
            Loại đầu cắm của xe
          </label>
          <select
            id="driver-connector"
            value={selectedConnector}
            onChange={(event) => {
              setConnector(event.target.value);
              onDepartureChange?.();
            }}
            aria-invalid={connectorInvalid}
            aria-describedby="driver-connector-help"
          >
            {connectorOptions.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
                {supportedConnectors.includes(value) ? "" : " (chưa có trạm)"}
              </option>
            ))}
          </select>
          <small id="driver-connector-help">
            {connectorInvalid
              ? "Chưa có trạm tương thích với đầu cắm này trong dữ liệu hiện tại."
              : "AC: sạc xoay chiều. DC: sạc một chiều. Chọn đúng cổng sạc trên xe."}
          </small>
        </div>
      </div>

      <div className="driver-toolbar__actions">
        <div className="driver-departure-note">
          <small id="driver-departure-help">
            Giờ Việt Nam ·{" "}
            {departureDraft !== null
              ? "Giờ khởi hành bạn chọn"
              : live
                ? "Khởi hành ngay"
                : "Theo mốc dữ liệu mô phỏng"}
          </small>
          {departureDraft !== null ? (
            <button
              type="button"
              className="departure-reset"
              onClick={() => {
                setDepartureDraft(null);
                onDepartureChange?.();
              }}
            >
              {live ? "Dùng giờ hiện tại" : "Dùng mốc dữ liệu"}
            </button>
          ) : null}
        </div>
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
          </div>
        </details>
      </div>

      <p
        id="trip-location-help"
        className="status-message driver-toolbar__hint"
      >
        {runtime?.places_available
          ? "Tìm địa điểm hoặc mở ▾ để chọn, rồi bấm Tìm kế hoạch sạc."
          : "Gõ rồi chọn địa điểm trong danh sách."}{" "}
        Chỉ các trạm có dữ liệu phù hợp mới được đề xuất.
        {runtime
          ? ` ${runtime.clock_mode === "replay" ? "Đang xem dữ liệu mô phỏng, không phải trạng thái trực tiếp." : runtime.clock_mode === "live" ? "Trạng thái từ nguồn trạm." : "Dữ liệu minh họa."}`
          : ""}
        <span className="driver-scenario-note">
          {scenario === "tet"
            ? "Tết: nhu cầu sạc mô phỏng cao."
            : scenario === "holiday_30_4"
              ? "Lễ 30/4: nhu cầu sạc mô phỏng tăng."
              : "Ngày thường: nhu cầu sạc mô phỏng cơ sở."}{" "}
          Tuyến đường có thể giống nhau; chưa mô phỏng ùn tắc theo ngày lễ.
        </span>
        {replay && historyReady ? (
          <span className="driver-history-range">
            Có dữ liệu từ{" "}
            {new Date(historyStart).toLocaleString("vi-VN", {
              timeZone: "Asia/Ho_Chi_Minh",
              hour: "2-digit",
              minute: "2-digit",
              day: "2-digit",
              month: "2-digit",
              year: "numeric",
            })}{" "}
            đến{" "}
            {new Date(historyEnd).toLocaleString("vi-VN", {
              timeZone: "Asia/Ho_Chi_Minh",
              hour: "2-digit",
              minute: "2-digit",
              day: "2-digit",
              month: "2-digit",
              year: "numeric",
            })}
            .
          </span>
        ) : null}
        {runtime?.observed_at && !timeInvalid ? (
          <span className="data-snapshot-note">
            Dữ liệu lúc{" "}
            <time dateTime={selectedObservation}>
              {new Date(selectedObservation).toLocaleString("vi-VN", {
                timeZone: "Asia/Ho_Chi_Minh",
                hour: "2-digit",
                minute: "2-digit",
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
              })}
            </time>{" "}
            (giờ Việt Nam) ·{" "}
            {replay && departureDraft !== null && inHistory
              ? "Phát lại snapshot lịch sử theo giờ khởi hành."
              : "Tự động lấy từ hệ thống."}
          </span>
        ) : null}
      </p>
      {runtimeLoading ? (
        <p className="connection-state" role="status">
          Đang kết nối dữ liệu trạm…
        </p>
      ) : runtimeError || (runtime && timeInvalid) ? (
        <div className="connection-state connection-state--error" role="alert">
          <span>
            {runtimeError ||
              "Chưa lấy được mốc dữ liệu trạm hợp lệ. Vui lòng thử kết nối lại."}
          </span>
          {onRetryRuntime ? (
            <button
              type="button"
              className="btn-secondary"
              onClick={onRetryRuntime}
            >
              Thử kết nối lại
            </button>
          ) : null}
        </div>
      ) : null}
      {invalid && !timeInvalid ? (
        <p className="field-error driver-toolbar__error" role="alert">
          {routeInvalid
            ? "Chọn hai địa điểm khác nhau trong danh sách gợi ý."
            : departureInvalid
              ? departureError
              : "Kiểm tra SOC (0–100), dung lượng pin > 0, tiêu hao > 0 và đầu cắm. Không để trống số."}
        </p>
      ) : null}
    </form>
  );
}

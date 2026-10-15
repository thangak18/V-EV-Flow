import { useEffect, useId, useRef, useState } from "react";
import { useApiClient } from "../../app/useApiClient";
import type { TripLocation } from "./corridorPresets";

// Keep the provider hook in a child: the offline native dropdown needs no API context.
export function PlaceSearch(props: {
  label: string;
  value: string;
  locations: TripLocation[];
  enabled: boolean;
  disabled?: boolean;
  resolved?: TripLocation;
  invalid: boolean;
  onChange: (value: string) => void;
  onResolve: (location: TripLocation) => void;
}) {
  if (props.enabled) return <RemotePlaceSearch {...props} />;
  return (
    <label className="field-chip">
      <span className="field-chip__label">{props.label}</span>
      <input
        type="text"
        disabled={props.disabled}
        list="trip-locations"
        autoComplete="off"
        value={props.value}
        placeholder="Gõ để chọn địa điểm…"
        aria-invalid={props.invalid}
        aria-describedby="trip-location-help"
        onChange={(event) => props.onChange(event.target.value)}
      />
    </label>
  );
}

function RemotePlaceSearch(props: Parameters<typeof PlaceSearch>[0]) {
  const client = useApiClient();
  const id = useId();
  const [session, setSession] = useState(() => crypto.randomUUID());
  const [items, setItems] = useState<
    { place_id: string; description: string }[]
  >([]);
  const [itemsQuery, setItemsQuery] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const detail = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const selected =
    props.resolved?.label === props.value ||
    props.locations.some((x) => x.label === props.value);
  useEffect(() => {
    const controller = new AbortController();
    if (props.value.trim().length < 2 || selected)
      return () => controller.abort();
    const timer = setTimeout(() => {
      setItemsQuery(props.value);
      setItems([]);
      setError("");
      setActive(-1);
      setBusy(true);
      client
        .searchPlaces(props.value, session, controller.signal)
        .then((result) => {
          if (!controller.signal.aborted) setItems(result.predictions);
        })
        .catch(() => {
          if (!controller.signal.aborted)
            setError(
              "Không tìm được địa chỉ qua Goong. Thử lại hoặc chọn trong danh mục.",
            );
        })
        .finally(() => {
          if (!controller.signal.aborted) setBusy(false);
        });
    }, 350);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [client, props.value, selected, session]);
  useEffect(() => () => detail.current?.abort(), []);
  const local = props.locations
    .filter((x) =>
      x.label
        .toLocaleLowerCase("vi")
        .includes(props.value.toLocaleLowerCase("vi")),
    )
    .slice(0, 5);
  const choices = [
    ...local.map((x) => ({ label: x.label, local: x, place_id: "" })),
    ...(itemsQuery === props.value ? items : []).map((x) => ({
      label: x.description,
      local: undefined as TripLocation | undefined,
      place_id: x.place_id,
    })),
  ];
  async function choose(index: number) {
    const choice = choices[index];
    if (!choice) return;
    if (choice.local) {
      props.onResolve(choice.local);
      setOpen(false);
      return;
    }
    detail.current?.abort();
    const controller = new AbortController();
    detail.current = controller;
    const version = ++generation.current;
    setBusy(true);
    setError("");
    try {
      const location = await client.resolvePlace(
        choice.place_id,
        session,
        controller.signal,
      );
      if (controller.signal.aborted || version !== generation.current) return;
      props.onResolve(location as TripLocation);
      setOpen(false);
      setSession(crypto.randomUUID());
    } catch {
      if (!controller.signal.aborted)
        setError("Không lấy được tọa độ. Hãy chọn lại địa chỉ.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <div className="field-chip place-search">
      <label htmlFor={id} className="field-chip__label">
        {props.label}
      </label>
      <input
        disabled={props.disabled}
        id={id}
        role="combobox"
        autoComplete="off"
        value={props.value}
        aria-autocomplete="list"
        aria-controls={`${id}-options`}
        aria-expanded={open}
        aria-activedescendant={active >= 0 ? `${id}-${active}` : undefined}
        aria-invalid={props.invalid}
        aria-describedby="trip-location-help"
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onChange={(event) => {
          generation.current++;
          detail.current?.abort();
          setBusy(false);
          setActive(-1);
          setError("");
          setItems([]);
          props.onChange(event.target.value);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpen(false);
            return;
          }
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
            setActive((previous) =>
              Math.max(
                0,
                Math.min(
                  choices.length - 1,
                  previous + (event.key === "ArrowDown" ? 1 : -1),
                ),
              ),
            );
          }
          if (event.key === "Enter" && open && active >= 0) {
            event.preventDefault();
            void choose(active);
          }
        }}
      />
      {open ? (
        <div className="place-search__dropdown">
          <ul
            id={`${id}-options`}
            role="listbox"
            aria-label={`Gợi ý ${props.label}`}
          >
            {choices.map((choice, index) => (
              <li
                id={`${id}-${index}`}
                key={choice.place_id || choice.label}
                role="option"
                aria-selected={index === active}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  void choose(index);
                }}
              >
                {choice.label}
              </li>
            ))}
          </ul>
          {busy ? <p role="status">Đang tìm địa chỉ…</p> : null}
          {error ? <p role="status">{error}</p> : null}
          {!busy && !error && !choices.length ? (
            <p>Không có gợi ý. Nhập thêm địa chỉ.</p>
          ) : null}
          <small>Địa chỉ từ Goong, trạm từ danh mục hiện có.</small>
        </div>
      ) : null}
    </div>
  );
}

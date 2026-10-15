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
  const input = useRef<HTMLInputElement>(null);
  const [source, setSource] = useState<"goong" | "demo">("goong");
  const [attempt, setAttempt] = useState(0);
  const query = props.value.trim();
  useEffect(() => {
    const controller = new AbortController();
    if (!open || source !== "goong" || query.length < 2)
      return () => controller.abort();
    const timer = setTimeout(() => {
      setItemsQuery(query);
      setItems([]);
      setError("");
      setActive(-1);
      setBusy(true);
      client
        .searchPlaces(query, session, controller.signal)
        .then((result) => {
          if (!controller.signal.aborted) setItems(result.predictions);
        })
        .catch(() => {
          if (!controller.signal.aborted)
            setError(
              "Không tìm được địa chỉ qua Goong. Thử lại hoặc chọn nguồn Danh mục demo.",
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
  }, [client, query, source, open, session, attempt]);
  useEffect(() => () => detail.current?.abort(), []);
  const normalized = (value: string) =>
    value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  const local = props.locations.filter((x) =>
    normalized(x.label).includes(normalized(query)),
  );
  const choices =
    source === "demo"
      ? local.map((x) => ({ label: x.label, local: x, place_id: "" }))
      : (itemsQuery === query ? items : []).map((x) => ({
          label: x.description,
          local: undefined as TripLocation | undefined,
          place_id: x.place_id,
        }));
  function edit(value: string) {
    generation.current++;
    detail.current?.abort();
    setBusy(false);
    setActive(-1);
    setError("");
    setItems([]);
    setItemsQuery("");
    props.onChange(value);
    setOpen(true);
  }
  function changeSource(next: "goong" | "demo") {
    generation.current++;
    detail.current?.abort();
    setSource(next);
    input.current?.focus();
    setActive(-1);
    setError("");
    setBusy(false);
  }
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
    <div
      className={`field-chip place-search ${open ? "place-search--open" : ""}`}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <label htmlFor={id} className="field-chip__label">
        {props.label}
      </label>
      <div className="place-search__input">
        <input
          ref={input}
          disabled={props.disabled}
          id={id}
          role="combobox"
          placeholder="Tìm và chọn địa điểm…"
          autoComplete="off"
          value={props.value}
          aria-autocomplete="list"
          aria-controls={`${id}-options`}
          aria-expanded={open}
          aria-activedescendant={active >= 0 ? `${id}-${active}` : undefined}
          aria-invalid={props.invalid}
          aria-describedby="trip-location-help"
          onFocus={() => setOpen(true)}
          onChange={(event) => edit(event.target.value)}
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
        <div className="place-search__buttons">
          {open && props.value ? (
            <button
              type="button"
              aria-label={`Xóa ${props.label}`}
              disabled={props.disabled}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                edit("");
                input.current?.focus();
              }}
            >
              <span aria-hidden>×</span>
            </button>
          ) : null}
          <button
            type="button"
            aria-label={`Mở danh sách ${props.label}`}
            disabled={props.disabled}
            aria-expanded={open}
            aria-controls={`${id}-options`}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              input.current?.focus();
              setOpen(!open);
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>
        </div>
      </div>
      {open ? (
        <div className="place-search__dropdown">
          <div
            className="place-search__sources"
            role="group"
            aria-label={`Lọc nguồn ${props.label}`}
          >
            <button
              type="button"
              aria-pressed={source === "goong"}
              onClick={() => changeSource("goong")}
            >
              Địa điểm Goong
            </button>
            <button
              type="button"
              aria-pressed={source === "demo"}
              onClick={() => changeSource("demo")}
            >
              Danh mục demo
            </button>
          </div>
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
          {source === "goong" &&
          (busy || (query.length >= 2 && itemsQuery !== query)) ? (
            <p role="status">Đang tìm địa điểm…</p>
          ) : null}
          {source === "goong" && error ? (
            <p role="status">
              {error}{" "}
              <button type="button" onClick={() => setAttempt(attempt + 1)}>
                Thử lại
              </button>
            </p>
          ) : null}
          {!busy && !error && !choices.length ? (
            <p>
              {source === "goong"
                ? query.length < 2
                  ? "Nhập từ 2 ký tự để tìm địa điểm trên bản đồ."
                  : itemsQuery === query
                    ? "Không tìm thấy địa điểm. Thử tên đường, quận hoặc thành phố."
                    : ""
                : "Không có địa điểm demo khớp bộ lọc."}
            </p>
          ) : null}
          <small>
            {source === "goong"
              ? "Chọn một gợi ý để lấy tọa độ từ Goong."
              : "Danh mục demo cố định, không phải kết quả tìm địa điểm Goong."}
          </small>
        </div>
      ) : null}
    </div>
  );
}

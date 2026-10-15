import { useState } from "react";
import type { Station } from "../../services/api";
import { PlaceSearch } from "../driver/PlaceSearch";
import type { TripLocation } from "../driver/corridorPresets";

import type { MonitoredArea } from "./areas";

export function AreaFilter({
  stations,
  placesAvailable,
  onApply,
}: {
  stations: Station[];
  placesAvailable: boolean;
  onApply: (area: MonitoredArea | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<TripLocation>();
  const [radiusKm, setRadius] = useState(25);
  const locations = stations.map((s) => ({
    label: s.name,
    lat: s.lat,
    lng: s.lng,
  }));
  const resolved =
    selected?.label === query
      ? selected
      : !placesAvailable
        ? locations.find((s) => s.label === query)
        : undefined;
  return (
    <section className="area-filter" aria-label="Chọn khu vực theo dõi">
      <div className="section-step">
        <span>01</span>
        <div>
          <h3>Chọn khu vực theo dõi</h3>
          <p>
            Tìm địa điểm hoặc chọn một trạm, sau đó lọc các trạm có dữ liệu xung
            quanh.
          </p>
        </div>
      </div>
      <div className="area-filter__fields">
        <PlaceSearch
          label="Khu vực theo dõi"
          value={query}
          locations={locations}
          enabled={placesAvailable}
          invalid={false}
          resolved={selected}
          onChange={(value) => {
            setQuery(value);
            setSelected(undefined);
          }}
          onResolve={(location) => {
            setQuery(location.label);
            setSelected(location);
          }}
        />
        <label className="field-chip">
          <span className="field-chip__label">Bán kính theo dõi</span>
          <select
            value={radiusKm}
            onChange={(event) => setRadius(Number(event.target.value))}
          >
            {[10, 25, 50, 100].map((km) => (
              <option key={km} value={km}>
                {km} km
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={!resolved}
          onClick={() => resolved && onApply({ center: resolved, radiusKm })}
        >
          Lọc khu vực
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            setQuery("");
            setSelected(undefined);
            onApply(null);
          }}
        >
          Toàn bộ mạng lưới
        </button>
      </div>
      {!placesAvailable ? (
        <datalist id="trip-locations">
          {locations.map((item) => (
            <option key={item.label} value={item.label} />
          ))}
        </datalist>
      ) : null}
    </section>
  );
}

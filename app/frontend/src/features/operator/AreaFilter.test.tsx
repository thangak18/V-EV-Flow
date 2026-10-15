import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import type { Station } from "../../services/api";
import { AreaFilter } from "./AreaFilter";
import { inMonitoredArea } from "./areas";

test("radius filtering includes nearby stations and never invents coverage", () => {
  const area = { center: { label: "A", lat: 10, lng: 106 }, radiusKm: 10 };
  expect(inMonitoredArea({ lat: 10.01, lng: 106 }, area)).toBe(true);
  expect(inMonitoredArea({ lat: 21, lng: 105 }, area)).toBe(false);
  expect(inMonitoredArea({ lat: 21, lng: 105 }, null)).toBe(true);
});

test("unknown place cannot apply until coordinates are selected; clear restores the network", () => {
  const onApply = vi.fn();
  const stations = [
    { station_id: "S1", name: "Trạm A", lat: 10, lng: 106 },
  ] as Station[];
  render(
    <AreaFilter
      stations={stations}
      placesAvailable={false}
      onApply={onApply}
    />,
  );
  const apply = screen.getByRole("button", { name: "Lọc khu vực" });
  expect(apply).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Khu vực theo dõi"), {
    target: { value: "Chưa chọn" },
  });
  expect(apply).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Khu vực theo dõi"), {
    target: { value: "Trạm A" },
  });
  fireEvent.change(screen.getByLabelText("Bán kính theo dõi"), {
    target: { value: "50" },
  });
  fireEvent.click(apply);
  expect(onApply).toHaveBeenLastCalledWith({
    center: { label: "Trạm A", lat: 10, lng: 106 },
    radiusKm: 50,
  });
  fireEvent.click(screen.getByRole("button", { name: "Toàn bộ mạng lưới" }));
  expect(onApply).toHaveBeenLastCalledWith(null);
});

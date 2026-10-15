import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { ApiProvider } from "../../app/ApiContext";
import { createMockApiClient } from "../../test/mockApiClient";
import { PlaceSearch } from "./PlaceSearch";

function setup(overrides = {}) {
  const onChange = vi.fn();
  const onResolve = vi.fn();
  const client = createMockApiClient({
    searchPlaces: vi.fn().mockResolvedValue({
      provider: "goong",
      predictions: [{ place_id: "place1", description: "Nhà hát" }],
    }),
    resolvePlace: vi.fn().mockResolvedValue({
      provider: "goong",
      place_id: "place1",
      label: "Nhà hát Thành phố",
      lat: 10.77,
      lng: 106.7,
    }),
    ...overrides,
  });
  const props = {
    label: "Điểm đi",
    value: "Nhà hát",
    locations: [],
    enabled: true,
    invalid: true,
    onChange,
    onResolve,
  };
  const view = render(
    <ApiProvider client={client}>
      <PlaceSearch {...props} />
    </ApiProvider>,
  );
  return { client, onChange, onResolve, ...view, props };
}

describe("remote place selection", () => {
  test("resolves an address with keyboard before changing selected coordinates", async () => {
    const { client, onResolve } = setup();
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    await screen.findByRole("option", { name: "Nhà hát" });
    expect(onResolve).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() =>
      expect(onResolve).toHaveBeenCalledWith(
        expect.objectContaining({
          label: "Nhà hát Thành phố",
          lat: 10.77,
          lng: 106.7,
        }),
      ),
    );
    expect(client.resolvePlace).toHaveBeenCalledTimes(1);
    expect(input).toHaveAttribute("aria-expanded", "false");
  });
  test("shows provider failure without inventing coordinates", async () => {
    const { onResolve } = setup({
      searchPlaces: vi.fn().mockRejectedValue(new Error("offline")),
    });
    fireEvent.focus(screen.getByRole("combobox"));
    expect(
      await screen.findByText(/Không tìm được địa chỉ qua Goong/),
    ).toBeInTheDocument();
    expect(onResolve).not.toHaveBeenCalled();
  });
  test("ignores late detail when the user edits the query", async () => {
    let resolveDetail!: (value: unknown) => void;
    const { onChange, onResolve } = setup({
      resolvePlace: vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveDetail = resolve;
          }),
      ),
    });
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    fireEvent.click(await screen.findByRole("option", { name: "Nhà hát" }));
    fireEvent.change(input, { target: { value: "Địa chỉ khác" } });
    resolveDetail({
      place_id: "place1",
      provider: "goong",
      label: "Cũ",
      lat: 10,
      lng: 106,
    });
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("Địa chỉ khác"));
    expect(onResolve).not.toHaveBeenCalled();
  });
  test("selects local coordinates without a provider detail request", async () => {
    const client = createMockApiClient();
    const onResolve = vi.fn();
    render(
      <ApiProvider client={client}>
        <PlaceSearch
          label="Điểm đi"
          value=""
          enabled
          invalid
          locations={[{ label: "Trạm A", lat: 10, lng: 106 }]}
          onChange={vi.fn()}
          onResolve={onResolve}
        />
      </ApiProvider>,
    );
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    fireEvent.click(screen.getByRole("option", { name: "Trạm A" }));
    expect(onResolve).toHaveBeenCalledWith({
      label: "Trạm A",
      lat: 10,
      lng: 106,
    });
  });
});

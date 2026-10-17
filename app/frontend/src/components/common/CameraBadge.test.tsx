import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { QueueObservation } from "../../services/api";
import { CameraBadge } from "./CameraBadge";
import { cameraSummary } from "./cameraSummary";

const view: QueueObservation = {
  station_id: "S001",
  observed_at: "2026-10-17T18:05:00+07:00",
  vehicles_waiting: 4,
  vehicles_charging: 2,
  confidence: 0.9,
  source: "camera_mock",
  data_type: "mock",
};

describe("CameraBadge", () => {
  test("shows the camera icon, queue and a full tooltip", () => {
    render(<CameraBadge observation={view} />);
    const badge = screen.getByLabelText(/Có camera/);
    expect(badge).toHaveTextContent("4 xe chờ");
    expect(badge).toHaveAttribute("title", cameraSummary(view));
    expect(cameraSummary(view)).toContain("minh họa");
    expect(cameraSummary(view)).toContain("18:05");
    expect(cameraSummary(view)).toContain("90%");
    expect(cameraSummary(view)).toContain("2 xe đang sạc");
  });

  test("renders nothing for a station without a camera", () => {
    const { container } = render(<CameraBadge observation={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  test("marks a poor camera view as weak", () => {
    render(<CameraBadge observation={{ ...view, confidence: 0.35 }} />);
    expect(screen.getByLabelText(/Có camera/)).toHaveClass(
      "camera-badge--weak",
    );
    expect(cameraSummary({ ...view, confidence: 0.35 })).toContain(
      "tín hiệu yếu",
    );
  });

  test("shows an empty queue as zero waiting", () => {
    render(<CameraBadge observation={{ ...view, vehicles_waiting: 0 }} />);
    expect(screen.getByLabelText(/Có camera/)).toHaveTextContent("0 xe chờ");
  });
});

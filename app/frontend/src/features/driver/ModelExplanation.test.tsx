import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { explanationFixture } from "../../test/p1Fixtures";
import { ModelExplanation } from "./ModelExplanation";

test("explains signed raw-margin contributions without presenting them as probability", () => {
  render(<ModelExplanation explanation={explanationFixture} />);
  fireEvent.click(screen.getByText("Vì sao có xác suất này? (TreeSHAP)"));
  expect(screen.getByText("Cổng trống hiện tại")).toBeInTheDocument();
  expect(screen.getByText("Số phút tới ETA")).toBeInTheDocument();
  expect(screen.getByText("Tăng điểm +0.500")).toBeInTheDocument();
  expect(screen.getByText("Giảm điểm -0.200")).toBeInTheDocument();
  expect(
    screen.getByText(/không cộng trực tiếp vào % xác suất/),
  ).toBeInTheDocument();
  expect(screen.queryByText("50%")).not.toBeInTheDocument();
});

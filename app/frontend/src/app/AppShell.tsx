import { useEffect, useState } from "react";

import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useApiClient } from "./useApiClient";

function BrandMark() {
  return (
    <svg
      className="brand-mark"
      width="28"
      height="28"
      viewBox="0 0 28 28"
      aria-hidden
    >
      <circle cx="6" cy="14" r="3.2" fill="currentColor" />
      <circle cx="22" cy="7" r="3.2" fill="currentColor" />
      <circle cx="22" cy="21" r="3.2" fill="currentColor" />
      <path
        d="M9 13.2 19 8.2M9 14.8 19 19.8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function AppShell() {
  const client = useApiClient();
  const operator = useLocation().pathname.startsWith("/operator");
  useEffect(() => {
    document.title = `${operator ? "Điều hành" : "Tài xế"} · V-EV Flow`;
  }, [operator]);
  const [runtime, setRuntime] = useState<Awaited<
    ReturnType<typeof client.ready>
  > | null>(null);
  const [runtimeError, setRuntimeError] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState(false);
  const [resetVersion, setResetVersion] = useState(0);
  const [resetComplete, setResetComplete] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    client
      .ready(controller.signal)
      .then((status) => {
        if (!controller.signal.aborted) {
          setRuntime(status);
          setRuntimeError(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setRuntimeError(true);
      });
    return () => controller.abort();
  }, [client]);

  async function resetDemo() {
    if (resetting) return;
    setResetting(true);
    setResetError(false);
    setResetComplete(false);
    try {
      const response = await client.reset({ contract_version: "0.1.0" });
      if (!response.reset) throw new Error("Reset was not confirmed");
      setResetVersion((version) => version + 1);
      setResetComplete(true);
    } catch {
      setResetError(true);
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className={`app-frame app-frame--${operator ? "operator" : "driver"}`}>
      <header className="app-topbar">
        <div className="brand-block">
          <BrandMark />
          <h1 className="brand-title">V-EV Flow</h1>
        </div>
        <span className="workspace-role">
          {operator ? "TRUNG TÂM ĐIỀU HÀNH" : "DÀNH CHO TÀI XẾ"}
        </span>
        <details
          className="workspace-menu"
          key={operator ? "operator" : "driver"}
        >
          <summary>
            Chuyển không gian <span aria-hidden>↗</span>
          </summary>
          <nav aria-label="Không gian làm việc">
            <NavLink
              to="/driver"
              className={({ isActive }) =>
                isActive ? "workspace-link nav-link--active" : "workspace-link"
              }
            >
              Tài xế
            </NavLink>
            <NavLink
              to="/operator"
              className={({ isActive }) =>
                isActive ? "workspace-link nav-link--active" : "workspace-link"
              }
            >
              Điều hành
            </NavLink>
          </nav>
        </details>
      </header>
      <div className="demo-controls">
        <p className="runtime-status" role="status">
          {runtimeError
            ? "Chưa xác minh được kết nối backend."
            : !runtime
              ? "Đang kiểm tra backend…"
              : !runtime.ready
                ? "Backend chưa sẵn sàng."
                : operator
                  ? runtime.predictor_backend === "model"
                    ? "Mô hình dự báo đã kết nối · Phân tích theo kịch bản"
                    : "Đang sử dụng dữ liệu minh họa"
                  : `${runtime.route_backend === "goong" ? "Chỉ đường tài xế: Goong" : "Chỉ đường tài xế mô phỏng — khoảng cách và ETA là giả định"} · ${runtime.predictor_backend === "model" ? "Mô hình đã huấn luyện" : "Dự đoán minh họa"}`}
        </p>
        <button
          type="button"
          className="btn-secondary"
          disabled={resetting}
          onClick={() => void resetDemo()}
        >
          {resetting ? "Đang đặt lại…" : "Đặt lại phiên"}
        </button>
      </div>
      {resetComplete ? (
        <p className="status-message" role="status">
          Đã đặt lại tải phân bổ. Bạn có thể bắt đầu kế hoạch mới.
        </p>
      ) : null}
      {resetError ? (
        <p className="field-error" role="alert">
          Chưa đặt lại được phiên. Kết quả đang xem vẫn được giữ; hãy thử lại.
        </p>
      ) : null}
      <Outlet key={resetVersion} />
    </div>
  );
}

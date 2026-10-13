import { NavLink, Outlet } from "react-router-dom";

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
  return (
    <div className="app-frame">
      <header className="app-topbar">
        <div className="brand-block">
          <BrandMark />
          <h1 className="brand-title">V-EV Flow</h1>
        </div>
        <nav className="app-nav" aria-label="Chính">
          <NavLink
            to="/driver"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link--active" : "nav-link"
            }
          >
            Tài xế
          </NavLink>
          <NavLink
            to="/operator"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link--active" : "nav-link"
            }
          >
            Điều hành
          </NavLink>
        </nav>
        <span className="data-badge data-badge--demo">Dữ liệu minh họa</span>
      </header>
      <Outlet />
    </div>
  );
}

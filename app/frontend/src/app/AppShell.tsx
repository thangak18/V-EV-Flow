import { NavLink, Outlet } from "react-router-dom";

export function AppShell() {
  return (
    <div className="app-frame">
      <header className="app-topbar">
        <div className="brand-block">
          <p className="brand-kicker">Corridor EV</p>
          <h1 className="brand-title">V-EV Flow</h1>
          <p className="brand-tagline">Hành lang sạc TP.HCM → Vũng Tàu</p>
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
      </header>
      <Outlet />
    </div>
  );
}

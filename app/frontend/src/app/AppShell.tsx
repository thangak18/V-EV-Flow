import { NavLink, Outlet } from "react-router-dom";

export function AppShell() {
  return (
    <div className="app-frame">
      <header className="app-topbar">
        <div className="brand-block">
          <h1 className="brand-title">V-EV Flow</h1>
          <p className="brand-tagline">Corridor charging planner</p>
        </div>
        <nav className="app-nav" aria-label="Primary">
          <NavLink
            to="/driver"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link--active" : "nav-link"
            }
          >
            Driver
          </NavLink>
          <NavLink
            to="/operator"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link--active" : "nav-link"
            }
          >
            Operator
          </NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  );
}

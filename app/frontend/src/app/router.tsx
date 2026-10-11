import { Navigate, Route, Routes } from "react-router-dom";

import { DriverPage } from "../pages/DriverPage";
import { OperatorPage } from "../pages/OperatorPage";
import { AppShell } from "./AppShell";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/driver" replace />} />
        <Route path="driver" element={<DriverPage />} />
        <Route path="operator" element={<OperatorPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/driver" replace />} />
    </Routes>
  );
}

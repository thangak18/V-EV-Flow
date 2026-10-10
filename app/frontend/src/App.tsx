import { ApiClient } from "./services/api";
import { MockStationList } from "./components/MockStationList";

function App() {
  const client = new ApiClient(import.meta.env.VITE_API_BASE_URL ?? "/api");

  return (
    <main className="app-shell">
      <header className="app-header">
        <p className="eyebrow">V-EV FLOW · PHASE 0</p>
        <h1>Charging stations</h1>
        <p className="subtitle">
          A small, transparent slice of the station data contract.
        </p>
      </header>
      <MockStationList client={client} />
    </main>
  );
}

export default App;

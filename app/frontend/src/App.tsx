import { BrowserRouter } from "react-router-dom";

import { ApiProvider } from "./app/ApiContext";
import { AppRouter } from "./app/router";
import { ApiClient } from "./services/api";

const client = new ApiClient(import.meta.env.VITE_API_BASE_URL ?? "/api");

function App() {
  return (
    <ApiProvider client={client}>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </ApiProvider>
  );
}

export default App;

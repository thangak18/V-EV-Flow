import { useContext } from "react";

import { ApiContext } from "./apiContextValue";

export function useApiClient() {
  const client = useContext(ApiContext);
  if (!client) {
    throw new Error("useApiClient must be used within ApiProvider");
  }
  return client;
}

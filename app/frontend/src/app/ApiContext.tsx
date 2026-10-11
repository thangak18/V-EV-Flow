import type { ReactNode } from "react";

import type { ApiClient } from "../services/api";
import { ApiContext } from "./apiContextValue";

export function ApiProvider({
  client,
  children,
}: {
  client: ApiClient;
  children: ReactNode;
}) {
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
}

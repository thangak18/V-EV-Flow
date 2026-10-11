import { createContext } from "react";

import type { ApiClient } from "../services/api";

export const ApiContext = createContext<ApiClient | null>(null);

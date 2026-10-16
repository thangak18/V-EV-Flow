import { useCallback, useEffect, useRef, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import {
  ApiError,
  type PressureResponse,
  type Scenario,
} from "../services/api";
import { isAbortError } from "../services/errors";

export type PressureStatus = "idle" | "loading" | "success" | "empty" | "error";

export function usePressure() {
  const client = useApiClient();
  const [status, setStatus] = useState<PressureStatus>("idle");
  const [result, setResult] = useState<PressureResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [requestKey, setRequestKey] = useState<string | null>(null);
  const [resultKey, setResultKey] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const load = useCallback(
    async (scenario: Scenario, time: string) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setStatus((current) => {
        if (current === "success") setStale(true);
        return "loading";
      });
      setError(null);
      setRequestKey(`${scenario}|${time}`);

      try {
        const response = await client.getPressure(
          { scenario, time },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setResult(response);
        setResultKey(`${scenario}|${time}`);
        setStale(false);
        setStatus(response.stations.length === 0 ? "empty" : "success");
      } catch (cause) {
        if (isAbortError(cause) || controller.signal.aborted) return;
        setError(cause instanceof ApiError ? cause.message : "Request failed");
        setStatus("error");
      }
    },
    [client],
  );

  useEffect(() => () => controllerRef.current?.abort(), []);

  return { status, result, error, stale, load, requestKey, resultKey };
}

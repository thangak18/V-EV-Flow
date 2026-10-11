import { useCallback, useRef, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import {
  ApiError,
  type RecommendationRequest,
  type RecommendationResult,
} from "../services/api";
import { isAbortError } from "../services/errors";

export type RecommendationStatus =
  "idle" | "loading" | "success" | "empty" | "error";

export function useRecommendation() {
  const client = useApiClient();
  const [status, setStatus] = useState<RecommendationStatus>("idle");
  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const lastRequestRef = useRef<RecommendationRequest | null>(null);

  const clear = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    lastRequestRef.current = null;
    setResult(null);
    setError(null);
    setStatus("idle");
  }, []);

  const submit = useCallback(
    async (request: RecommendationRequest) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      lastRequestRef.current = request;
      setStatus("loading");
      setError(null);

      try {
        const response = await client.recommend(request, controller.signal);
        if (controller.signal.aborted) return;
        setResult(response);
        const empty = response.primary == null && response.backup == null;
        setStatus(empty ? "empty" : "success");
      } catch (cause) {
        if (isAbortError(cause) || controller.signal.aborted) return;
        setError(cause instanceof ApiError ? cause.message : "Request failed");
        setStatus("error");
      }
    },
    [client],
  );

  const retry = useCallback(() => {
    if (lastRequestRef.current) {
      void submit(lastRequestRef.current);
    }
  }, [submit]);

  return { status, result, error, submit, retry, clear };
}

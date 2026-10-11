import { useCallback, useState } from "react";

import { useApiClient } from "../app/useApiClient";
import type { Scenario, SimulationResult, Strategy } from "../services/api";

const STRATEGIES: Strategy[] = [
  "nearest",
  "currently_available",
  "ai_allocation",
];

export type StrategyRow =
  | { strategy: Strategy; status: "success"; result: SimulationResult }
  | { strategy: Strategy; status: "error"; message: string };

export function useSimulationComparison() {
  const client = useApiClient();
  const [pending, setPending] = useState(false);
  const [rows, setRows] = useState<StrategyRow[]>([]);
  const [config, setConfig] = useState<{
    scenario: Scenario;
    seed: number;
    vehicleCount: number;
  } | null>(null);

  const run = useCallback(
    async (scenario: Scenario, seed: number, vehicleCount: number) => {
      setPending(true);
      setConfig({ scenario, seed, vehicleCount });
      const settled = await Promise.allSettled(
        STRATEGIES.map((strategy) =>
          client.simulate({
            scenario,
            seed,
            vehicle_count: vehicleCount,
            strategy,
            contract_version: "0.1.0",
          }),
        ),
      );

      setRows(
        settled.map((entry, index) => {
          const strategy = STRATEGIES[index]!;
          if (entry.status === "fulfilled") {
            return {
              strategy,
              status: "success" as const,
              result: entry.value,
            };
          }
          const message =
            entry.reason instanceof Error
              ? entry.reason.message
              : "Simulation failed";
          return { strategy, status: "error" as const, message };
        }),
      );
      setPending(false);
    },
    [client],
  );

  return { pending, rows, config, run };
}

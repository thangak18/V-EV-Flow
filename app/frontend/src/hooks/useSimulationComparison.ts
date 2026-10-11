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

type RunConfig = {
  scenario: Scenario;
  seed: number;
  vehicleCount: number;
};

function mismatchMessage(
  result: SimulationResult,
  requested: RunConfig & { strategy: Strategy },
): string | null {
  if (result.strategy !== requested.strategy) {
    return `Response strategy ${result.strategy} does not match requested ${requested.strategy}`;
  }
  if (result.scenario !== requested.scenario) {
    return `Response scenario ${result.scenario} does not match requested ${requested.scenario}`;
  }
  if (result.seed !== requested.seed) {
    return `Response seed ${result.seed} does not match requested ${requested.seed}`;
  }
  if (result.metrics.vehicle_count !== requested.vehicleCount) {
    return `Response vehicle_count ${result.metrics.vehicle_count} does not match requested ${requested.vehicleCount}`;
  }
  return null;
}

function withConsistentFixtureHash(rows: StrategyRow[]): StrategyRow[] {
  const successHashes = rows
    .filter(
      (row): row is Extract<StrategyRow, { status: "success" }> =>
        row.status === "success",
    )
    .map((row) => row.result.fixture_hash);
  const unique = new Set(successHashes);
  if (unique.size <= 1) return rows;

  return rows.map((row) =>
    row.status === "success"
      ? {
          strategy: row.strategy,
          status: "error" as const,
          message:
            "fixture_hash mismatch across strategies — comparison aborted",
        }
      : row,
  );
}

export function useSimulationComparison() {
  const client = useApiClient();
  const [pending, setPending] = useState(false);
  const [rows, setRows] = useState<StrategyRow[]>([]);
  const [config, setConfig] = useState<RunConfig | null>(null);

  const run = useCallback(
    async (scenario: Scenario, seed: number, vehicleCount: number) => {
      setPending(true);
      const runConfig: RunConfig = { scenario, seed, vehicleCount };
      setConfig(runConfig);
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

      const nextRows = settled.map((entry, index): StrategyRow => {
        const strategy = STRATEGIES[index]!;
        if (entry.status !== "fulfilled") {
          const message =
            entry.reason instanceof Error
              ? entry.reason.message
              : "Simulation failed";
          return { strategy, status: "error", message };
        }

        const mismatch = mismatchMessage(entry.value, {
          ...runConfig,
          strategy,
        });
        if (mismatch) {
          return { strategy, status: "error", message: mismatch };
        }

        return {
          strategy,
          status: "success",
          result: entry.value,
        };
      });

      setRows(withConsistentFixtureHash(nextRows));
      setPending(false);
    },
    [client],
  );

  return { pending, rows, config, run };
}

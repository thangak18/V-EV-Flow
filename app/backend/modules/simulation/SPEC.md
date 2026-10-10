# Simulation Module Specification — A/Bảo

## Objective

Implement a stateful 5-minute charging simulator and a reproducible 100-vehicle comparison runner for `nearest`, `currently_available`, and injected `ai_allocation` strategies.

## Inputs and Public Output

Inputs are validated station/scenario/vehicle fixtures plus an `AllocationStrategy` port. Output implements `SimulationRunner` and returns metrics and a manifest matching shared contracts: success rate at arrival, mean detour, mean wait, failed count, vehicle count, scenario, seed, strategy, data version, and model version when applicable.

## Invariants

Charging sessions, queues, failures, and repairs persist across steps. All strategies receive identical pre-generated background arrivals, service durations, faults, vehicles, and seed. Failed vehicles remain in the denominator. Simulation state never shares Driver virtual-load state.

## Freedom and Non-goals

Bảo may choose NumPy/pandas structures and add SimPy only when useful. The module does not train models, implement HTTP endpoints, call Goong, or know recommendation internals. What-if is P1 after the three P0 strategies work.

## Required Tests and Done Criteria

Test reproducibility, capacity conservation, queue continuity, failure/repair transitions, equal fixtures across strategies, metric definitions, empty/capacity-zero cases, and strategy injection. Done means one documented command produces schema-valid results for all three scenarios and three strategies without hard-coded winners.

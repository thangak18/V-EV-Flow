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

## Engine and Status History (implemented)

`SimulationEngine` advances five-minute steps. Events at one timestamp apply in this order: repairs, faults, completions, arrivals, queue admission, snapshot. Queues are FIFO. A port that breaks while all healthy ports are busy interrupts the session with the most remaining time; that vehicle returns to the head of the queue with its remaining minutes. Every snapshot satisfies `free + busy + broken == n_ports`.

`generate_status_history(bundle, stations, config)` replays a `FixtureBundle` into the canonical `station_status` frame; `write_status_history` validates and writes Parquet; `build_status_window` builds a `StatusWindow` that never contains timestamps after `observed_at`. `python -m app.backend.modules.simulation.cli history --input <station_data output>` writes the Parquet; see the station-data SPEC for the full two-command flow.

## Runner and Comparison (implemented)

```bash
uv run python -m app.backend.modules.simulation.cli compare \
  --input app/backend/modules/station_data/generated --scenario all --vehicles 100
```

Run `station_data.cli generate` first. Writes `compare_results.json` (`SimulationResult` per scenario and strategy) and prints a table plus the `fixture_hash` per scenario. `ai_allocation` runs only with `--ai-strategy package.module:attribute` (an object with `select`, or a zero-argument factory); this module never imports recommendation.

`DefaultSimulationRunner(fixture_loader, stations, configs, availability=None, ...)` replays each strategy independently from one immutable `FixtureBundle`. Vehicle trips (id, origin, destination, departure, compliance) derive from `bundle.seed` in `trips.py`, because the shared `Vehicle` has no identity or position. Vehicles depart in the last 20 hours of the first 24-hour block ending 4 hours before the window end; earlier days only warm up background load. `availability(station_id, observed_at, eta)` supplies `p_available`; the default is persistence (1.0 if a port is free now, else 0.0). Inject a predictor-backed function for `ai_allocation`.

Metric definitions (also in `metrics.py`):

- `success_rate`: vehicles that found a free port on arrival / `vehicle_count`. Served-after-wait is not a success.
- `failed_count`: no feasible station or plan, waited longer than the maximum wait (30 min), or never arrived inside the window.
- `mean_detour_km`: over vehicles assigned a station. `mean_wait_minutes`: over vehicles that reached a station; abandoned vehicles count the maximum wait.

Assumptions (configurable): road distance 1.3 x straight line, 50 km/h, charge to 80% at 90% efficiency, 10% SOC reserve, no diversion to the backup, non-compliant drivers (`1 - compliance_rate`) go to the nearest feasible station. The backup station is therefore not exercised yet.

## Wiring into the API (composition root)

Import only from `app.backend.modules.simulation.public`. The simulation module cannot import `station_data` or `recommendation`, so the composition root supplies the loader and the AI strategy:

```python
from functools import lru_cache

from app.backend.modules.simulation.public import DefaultSimulationRunner, strategy_for
from app.backend.modules.station_data.public import (
    generate_fixture_bundle, load_scenarios, load_stations,
)

stations = load_stations(STATIONS_PATH)
configs = load_scenarios(SCENARIOS_PATH)

@lru_cache(maxsize=16)
def _bundle(scenario, seed, vehicle_count):
    config = configs[scenario].model_copy(update={"seed": seed})
    return generate_fixture_bundle(config, stations, vehicle_count)

runner = DefaultSimulationRunner(
    lambda req: _bundle(req.scenario, req.seed, req.vehicle_count),
    stations,
    configs,
    availability=predictor_backed_fn,  # (station_id, observed_at, eta) -> p_available
)
strategy = strategy_for(runner, request.strategy, ai_strategy=recommendation_strategy)
result = runner.run(request, strategy)
```

- `strategy_for` maps `Strategy` to a strategy object. `ai_allocation` raises `ValueError` unless an `AllocationStrategy` is injected; there is no silent fallback to a baseline.
- Each `Strategy` run uses a fresh engine from the same bundle, so all results for one `(scenario, seed, vehicle_count)` share `fixture_hash`.
- The runner is not thread-safe (`free_ports` reflects the run in progress); the demo uses one worker.

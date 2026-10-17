# Station Data Module Specification — A/Bảo

## Objective

Provide canonical, source-labelled station metadata, scenario configuration, deterministic vehicle/background fixtures, and validation needed by simulation, prediction, and API adapters.

## Owned Output

- 10–20 TP.HCM–Vũng Tàu stations with source and explicit assumptions.
- `normal`, `holiday_30_4`, and `tet` scenario configs with seed and 5-minute step.
- Small committed fixtures for CI and separately generated large datasets ignored by Git.
- Manifests recording schema/data version, seed, config, creation time, and data origin.

All files validate against shared contracts. Station IDs are stable; status counts are non-negative and sum to capacity; timestamps carry `+07:00`; generated records are unique by scenario/station/time.

## Boundaries

This module must not import prediction, recommendation, API, or infrastructure internals. It may expose validators and fixture-generation entry points through its public package. Storage implementations belong to infrastructure.

## Required Tests and Done Criteria

Test invalid stations, port conservation, timestamps, scenario enums, deterministic seed output, fixture manifests, and schema round-trips. Done means other modules can consume committed fixtures without importing station-data internals and all data is labelled real, assumed, mock, simulated, or mixed correctly.

## Generating Data (reproducible)

```bash
uv run python -m app.backend.modules.station_data.cli generate \
  --scenario all --seed 42 --output app/backend/modules/station_data/generated \
&& uv run python -m app.backend.modules.simulation.cli history \
  --input app/backend/modules/station_data/generated
```

Domain modules cannot import each other (architecture test), so generation is two commands joined by `&&`; the interface between them is files validated by shared contracts.

Step 1 (`station_data.cli generate`) writes `stations.json`, per-scenario `<scenario>/fixture_bundle.json` + `manifest.json`, and a top-level `manifest.json` (`data_version`, `data_type="simulated"`, seed, `generated_at`, and per scenario: counts, `fixture_hash`, `history_days`, window `config`). Step 2 (`simulation.cli history`) replays each bundle and writes `station_status.parquet` (columns `station_id, ts, ports_free, ports_busy, ports_broken, scenario`; unique by `(scenario, station_id, ts)`; `+07:00`), then adds `status_history` (file, rows, SHA-256) to `manifest.json`. Output is git-ignored; never commit it.

- `--history-days` (default `history_days` from `scenarios.yaml`, 14) sets history length. `--history-end` (ISO time or `today` for 23:55 of the current +07:00 day; default: end of the `normal` scenario) is shared by all scenarios so one global temporal train/calibration/test split sees every scenario.
- Same seed and options give identical `fixture_hash` and Parquet rows; `generated_at` is the only time-varying field.
- `ScenarioSpec` (loaders) holds parameters absent from the shared `ScenarioConfig` and maps to it; `holiday_multiplier` is informational because holiday demand is already in `arrival_multiplier` and the day coefficients.
- Capacity, power, demand coefficients, and fault/repair rates are synthetic assumptions.

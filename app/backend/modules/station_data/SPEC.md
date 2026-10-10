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

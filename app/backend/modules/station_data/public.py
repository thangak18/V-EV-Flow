"""Stable station-data entry point for other modules."""

from app.backend.modules.station_data.generator import generate_fixture_bundle, step_times
from app.backend.modules.station_data.loaders import (
    SCENARIOS_PATH,
    STATIONS_PATH,
    ScenarioSpec,
    load_scenario_specs,
    load_scenarios,
    load_stations,
)
from app.backend.modules.station_data.manifests import (
    DATA_VERSION,
    build_manifest,
    fixture_hash,
    load_fixture_bundle,
    write_fixture_bundle,
)

__all__ = [
    "DATA_VERSION",
    "SCENARIOS_PATH",
    "STATIONS_PATH",
    "ScenarioSpec",
    "build_manifest",
    "fixture_hash",
    "generate_fixture_bundle",
    "load_fixture_bundle",
    "load_scenario_specs",
    "load_scenarios",
    "load_stations",
    "step_times",
    "write_fixture_bundle",
]

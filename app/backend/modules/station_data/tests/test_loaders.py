import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.backend.contracts.enums import Scenario
from app.backend.modules.station_data.loaders import (
    SCENARIOS_PATH,
    STATIONS_PATH,
    load_scenario_specs,
    load_scenarios,
    load_stations,
)


def test_load_stations_returns_unique_corridor_ids() -> None:
    stations = load_stations(STATIONS_PATH)
    ids = [station.station_id for station in stations]
    assert 10 <= len(stations) <= 20
    assert len(set(ids)) == len(ids)
    assert {"S001", "S002"} <= set(ids)
    assert all(station.assumptions and station.source for station in stations)
    assert all("CCS2" in station.connector_types for station in stations)


def test_load_stations_rejects_duplicate_ids(tmp_path: Path) -> None:
    rows = json.loads(STATIONS_PATH.read_text())
    path = tmp_path / "stations.json"
    path.write_text(json.dumps([rows[0], rows[0]]))
    with pytest.raises(ValueError, match="unique"):
        load_stations(path)


def test_load_stations_rejects_invalid_station(tmp_path: Path) -> None:
    rows = json.loads(STATIONS_PATH.read_text())
    rows[0]["n_ports"] = 0
    path = tmp_path / "stations.json"
    path.write_text(json.dumps(rows))
    with pytest.raises(ValidationError):
        load_stations(path)


def test_all_scenarios_use_five_minute_steps() -> None:
    scenarios = load_scenarios(SCENARIOS_PATH)
    assert set(scenarios) == {Scenario.NORMAL, Scenario.HOLIDAY_30_4, Scenario.TET}
    assert all(item.step_minutes == 5 for item in scenarios.values())
    assert all(item.seed == 42 for item in scenarios.values())


def test_contract_config_maps_internal_names() -> None:
    spec = load_scenario_specs(SCENARIOS_PATH)[Scenario.TET]
    config = load_scenarios(SCENARIOS_PATH)[Scenario.TET]
    assert config.demand_multiplier == spec.arrival_multiplier == 1.40
    assert config.compliance_rate == spec.suggestion_compliance == 0.70


def _write_mutated(tmp_path: Path, mutate) -> Path:  # noqa: ANN001
    payload = yaml.safe_load(SCENARIOS_PATH.read_text())
    mutate(payload["scenarios"]["normal"], payload)
    path = tmp_path / "scenarios.yaml"
    path.write_text(yaml.safe_dump(payload))
    return path


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s, p: s.update(fault_probability=1.5),
        lambda s, p: s.update(repair_probability=-0.1),
        lambda s, p: s.update(suggestion_compliance=2),
        lambda s, p: s.update(charging_minutes=[45, 20]),
        lambda s, p: s.update(start="2026-10-14T00:00:00+07:00"),
        lambda s, p: s.update(start="2026-10-13T00:00:00+00:00"),
        lambda s, p: s.update(history_days=0),
        lambda s, p: s["demand_arrival_coefficients"]["by_hour"].pop("00"),
        lambda s, p: s["demand_arrival_coefficients"]["by_day"].pop("sunday"),
        lambda s, p: p.update(step_minutes=10),
    ],
)
def test_invalid_scenario_values_are_rejected(tmp_path: Path, mutate) -> None:  # noqa: ANN001
    with pytest.raises((ValidationError, ValueError)):
        load_scenario_specs(_write_mutated(tmp_path, mutate))


def test_missing_scenario_is_rejected(tmp_path: Path) -> None:
    path = _write_mutated(tmp_path, lambda s, p: p["scenarios"].pop("tet"))
    with pytest.raises(ValueError, match="every Scenario"):
        load_scenario_specs(path)

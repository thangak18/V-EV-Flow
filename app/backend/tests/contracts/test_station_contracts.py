import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType, Scenario, Strategy
from app.backend.contracts.stations import Station, StationListResponse, StationStatus


def test_station_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Station.model_validate(
            {
                "station_id": "S001",
                "name": "A",
                "lat": 10.7,
                "lng": 106.7,
                "n_ports": 2,
                "power_kw": 120,
                "connector_types": ["CCS2"],
                "network": "demo",
                "station_type": "highway",
                "source": "fixture",
                "assumptions": [],
                "extra_value": 1,
            }
        )


def test_status_conserves_ports() -> None:
    with pytest.raises(ValidationError):
        StationStatus(
            station_id="S001",
            ts=datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
            ports_free=1,
            ports_busy=1,
            ports_broken=1,
            n_ports=2,
            scenario=Scenario.NORMAL,
        )


def test_models_enforce_coordinate_and_timezone_bounds() -> None:
    with pytest.raises(ValidationError):
        Coordinate(lat=91, lng=106)
    with pytest.raises(ValidationError):
        StationStatus(
            station_id="S001",
            ts=datetime(2026, 10, 13, 16),
            ports_free=2,
            ports_busy=0,
            ports_broken=0,
            n_ports=2,
            scenario=Scenario.NORMAL,
        )


def test_fixture_stations_validate_and_response_round_trips() -> None:
    root = Path(__file__).parents[3]
    rows = json.loads((root / "backend/modules/station_data/fixtures/stations.json").read_text())
    stations = tuple(Station.model_validate(row) for row in rows)
    assert [station.station_id for station in stations] == ["S001", "S002"]
    response = StationListResponse(
        stations=stations, data_type=DataType.MIXED, source_notes=["Synthetic phase0 fixture"]
    )
    assert StationListResponse.model_validate_json(response.model_dump_json()) == response


def test_committed_station_response_example_validates() -> None:
    root = Path(__file__).parents[3]
    payload = json.loads((root / "backend/contracts/examples/stations.response.json").read_text())
    response = StationListResponse.model_validate(payload)
    assert [station.station_id for station in response.stations] == ["S001", "S002"]


def test_scenarios_are_explicit_and_deterministic() -> None:
    root = Path(__file__).parents[3]
    payload = yaml.safe_load(
        (root / "backend/modules/station_data/fixtures/scenarios.yaml").read_text()
    )
    assert payload["seed"] == 42
    assert payload["step_minutes"] == 5
    assert set(payload["scenarios"]) == {item.value for item in Scenario}
    for scenario in payload["scenarios"].values():
        coefficients = scenario["demand_arrival_coefficients"]
        assert coefficients["by_hour"]
        assert coefficients["by_day"]
        assert coefficients["by_station_type"]
        assert scenario["source"]
        assert scenario["assumptions"]


def test_enums_are_stable() -> None:
    assert Scenario("normal") is Scenario.NORMAL
    assert DataType("simulated") is DataType.SIMULATED
    assert Strategy("nearest") is Strategy.NEAREST

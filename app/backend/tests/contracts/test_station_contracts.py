import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType, Scenario, Strategy
from app.backend.contracts.stations import Station, StationListResponse, StationStatus


def test_station_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Station.model_validate({"station_id": "S001", "name": "A", "lat": 10.7, "lng": 106.7,
                                "n_ports": 2, "power_kw": 120, "connector_types": ["CCS2"],
                                "network": "demo", "station_type": "highway", "source": "fixture",
                                "assumptions": [], "extra_value": 1})


def test_status_conserves_ports() -> None:
    with pytest.raises(ValidationError):
        StationStatus(station_id="S001", ts=datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
                      ports_free=1, ports_busy=1, ports_broken=1,
                      n_ports=2, scenario=Scenario.NORMAL)


def test_models_enforce_coordinate_and_timezone_bounds() -> None:
    with pytest.raises(ValidationError):
        Coordinate(lat=91, lng=106)
    with pytest.raises(ValidationError):
        StationStatus(station_id="S001", ts=datetime(2026, 10, 13, 16), ports_free=2,
                      ports_busy=0, ports_broken=0, n_ports=2, scenario=Scenario.NORMAL)


def test_fixture_stations_validate_and_response_round_trips() -> None:
    root = Path(__file__).parents[3]
    rows = json.loads((root / "backend/modules/station_data/fixtures/stations.json").read_text())
    stations = tuple(Station.model_validate(row) for row in rows)
    assert [station.station_id for station in stations] == ["S001", "S002"]
    response = StationListResponse(stations=stations, data_type=DataType.MIXED,
                                   source_notes=["Synthetic phase0 fixture"])
    assert StationListResponse.model_validate_json(response.model_dump_json()) == response


def test_enums_are_stable() -> None:
    assert Scenario("normal") is Scenario.NORMAL
    assert DataType("simulated") is DataType.SIMULATED
    assert Strategy("nearest") is Strategy.NEAREST

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.ports import QueueObservationSource
from app.backend.contracts.queue import QueueObservation
from app.backend.infrastructure.repositories.mock import MockStationRepository
from app.backend.infrastructure.services.camera_mock import MockCameraQueueSource

VN = timezone(timedelta(hours=7))
EVENING = datetime(2026, 10, 17, 18, 2, tzinfo=VN)
NIGHT = datetime(2026, 10, 17, 3, 2, tzinfo=VN)
STATIONS = MockStationRepository().list_stations()
IDS = [station.station_id for station in STATIONS]


def source(**overrides: object) -> MockCameraQueueSource:
    return MockCameraQueueSource(STATIONS, **overrides)  # type: ignore[arg-type]


def observed(src: MockCameraQueueSource, at: datetime, scenario: Scenario = Scenario.NORMAL):
    return [src.observe(station_id, at, scenario) for station_id in IDS]


def total_waiting(src: MockCameraQueueSource, at: datetime, scenario: Scenario) -> int:
    return sum(o.vehicles_waiting for o in observed(src, at, scenario) if o is not None)


def test_implements_the_port() -> None:
    assert isinstance(source(), QueueObservationSource)


def test_only_a_share_of_stations_have_cameras() -> None:
    covered = [o for o in observed(source(), EVENING) if o is not None]
    assert 0.3 * len(IDS) <= len(covered) <= 0.8 * len(IDS)
    assert len(covered) < len(IDS)


def test_camera_coverage_is_the_same_at_any_time_or_scenario() -> None:
    src = source()
    has_camera = {s for s, o in zip(IDS, observed(src, EVENING), strict=True) if o}
    other = {s for s, o in zip(IDS, observed(src, NIGHT, Scenario.TET), strict=True) if o}
    assert has_camera == other


def test_observation_is_a_valid_mock_contract_object() -> None:
    first = next(o for o in observed(source(), EVENING) if o is not None)
    assert isinstance(first, QueueObservation)
    assert first.source == "camera_mock"
    assert first.data_type is DataType.MOCK
    assert first.observed_at.tzinfo is not None
    assert first.observed_at <= EVENING
    assert EVENING - first.observed_at < timedelta(minutes=5)
    assert first.observed_at.minute % 5 == 0


def test_same_seed_is_reproducible_and_other_seed_differs() -> None:
    assert observed(source(seed=7), EVENING) == observed(source(seed=7), EVENING)
    assert observed(source(seed=7), EVENING) != observed(source(seed=8), EVENING)


def test_peak_hour_is_busier_than_night() -> None:
    src = source()
    assert total_waiting(src, EVENING, Scenario.NORMAL) > total_waiting(src, NIGHT, Scenario.NORMAL)


def test_holiday_scenarios_are_busier_than_normal() -> None:
    src = source()
    normal = total_waiting(src, EVENING, Scenario.NORMAL)
    assert total_waiting(src, EVENING, Scenario.HOLIDAY_30_4) > normal
    assert total_waiting(src, EVENING, Scenario.TET) > normal


def test_confidence_varies_and_some_views_are_unreliable() -> None:
    values = {
        o.confidence
        for hour in range(24)
        for o in observed(source(), EVENING.replace(hour=hour))
        if o is not None
    }
    assert all(0 <= value <= 1 for value in values)
    assert min(values) < 0.6
    assert max(values) > 0.8


def test_charging_never_exceeds_station_ports() -> None:
    ports = {station.station_id: station.n_ports for station in STATIONS}
    for hour in range(24):
        for station_id, o in zip(IDS, observed(source(), EVENING.replace(hour=hour)), strict=True):
            if o is not None:
                assert o.vehicles_charging <= ports[station_id]


def test_override_forces_the_demo_jam_and_removes_cameras(tmp_path: Path) -> None:
    config = tmp_path / "camera.json"
    config.write_text(
        json.dumps(
            {
                "seed": 7,
                "coverage": 0.5,
                "force_camera": [IDS[0]],
                "no_camera": [IDS[1]],
                "overrides": {
                    IDS[0]: {"vehicles_waiting": 9, "vehicles_charging": 4, "confidence": 0.95}
                },
            }
        )
    )
    src = MockCameraQueueSource(STATIONS, config_path=config)
    jam = src.observe(IDS[0], NIGHT, Scenario.NORMAL)
    assert jam is not None
    assert (jam.vehicles_waiting, jam.vehicles_charging, jam.confidence) == (9, 4, 0.95)
    assert src.observe(IDS[1], EVENING, Scenario.TET) is None


def test_config_naming_an_unknown_station_is_rejected(tmp_path: Path) -> None:
    config = tmp_path / "camera.json"
    config.write_text(json.dumps({"seed": 1, "coverage": 0.5, "force_camera": ["NOPE"]}))
    with pytest.raises(ValueError, match="NOPE"):
        MockCameraQueueSource(STATIONS, config_path=config)


def test_unknown_station_has_no_camera() -> None:
    assert source().observe("NOPE", EVENING, Scenario.NORMAL) is None


def test_naive_time_is_rejected() -> None:
    with pytest.raises(ValueError):
        source().observe(IDS[0], datetime(2026, 10, 17, 18, 2), Scenario.NORMAL)


def test_non_local_timezone_input_is_accepted() -> None:
    src = source()
    assert observed(src, EVENING) == observed(src, EVENING.astimezone(UTC))

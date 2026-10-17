from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.backend.contracts.enums import DataType
from app.backend.contracts.ports import QueueObservationSource
from app.backend.contracts.queue import QueueObservation

VALID = {
    "station_id": "S001",
    "observed_at": "2026-10-17T14:05:00+07:00",
    "vehicles_waiting": 4,
    "vehicles_charging": 2,
    "confidence": 0.9,
    "source": "camera_mock",
    "data_type": "mock",
}


def test_valid_observation_parses() -> None:
    observation = QueueObservation.model_validate(VALID)
    assert observation.vehicles_waiting == 4
    assert observation.data_type is DataType.MOCK


def test_observation_rejects_naive_time() -> None:
    with pytest.raises(ValidationError):
        QueueObservation.model_validate({**VALID, "observed_at": "2026-10-17T14:05:00"})


@pytest.mark.parametrize(
    "patch",
    [
        {"vehicles_waiting": -1},
        {"vehicles_charging": -1},
        {"confidence": 1.1},
        {"confidence": -0.1},
        {"station_id": ""},
        {"source": ""},
        {"unknown": 1},
    ],
)
def test_observation_rejects_invalid_values(patch: dict) -> None:
    with pytest.raises(ValidationError):
        QueueObservation.model_validate({**VALID, **patch})


def test_queue_source_port_is_runtime_checkable() -> None:
    class Source:
        def observe(self, station_id: str, at: datetime, scenario) -> QueueObservation | None:
            return None

    assert isinstance(Source(), QueueObservationSource)


def test_committed_example_matches_contract() -> None:
    path = Path(__file__).parents[2] / "contracts" / "examples" / "queue.response.json"
    QueueObservation.model_validate_json(path.read_text())


def test_snapshot_lists_only_stations_that_have_cameras() -> None:
    from app.backend.contracts.queue import QueueSnapshotResponse

    snapshot = QueueSnapshotResponse.model_validate(
        {
            "observed_at": "2026-10-17T14:05:00+07:00",
            "scenario": "tet",
            "observations": [VALID],
            "data_type": "mock",
            "source_notes": ["Mock cameras cover some stations."],
        }
    )
    assert [o.station_id for o in snapshot.observations] == ["S001"]


def test_snapshot_rejects_duplicate_stations_and_naive_time() -> None:
    from app.backend.contracts.queue import QueueSnapshotResponse

    base = {
        "observed_at": "2026-10-17T14:05:00+07:00",
        "scenario": "normal",
        "observations": [VALID, VALID],
        "data_type": "mock",
        "source_notes": [],
    }
    with pytest.raises(ValidationError):
        QueueSnapshotResponse.model_validate(base)
    with pytest.raises(ValidationError):
        QueueSnapshotResponse.model_validate(
            {**base, "observations": [VALID], "observed_at": "2026-10-17T14:05:00"}
        )

"""Contract-facing tests for bounded file-backed repository adapters."""

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.backend.api.errors import domain_error_handler
from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import (
    DataSourceUnavailableError,
    DomainError,
    StationNotFoundError,
)
from app.backend.contracts.ports import StationRepository, StatusRepository
from app.backend.tests.conformance.repository_contract import StationRepositoryContract

UTC_PLUS_7 = timezone(timedelta(hours=7))


def _files_module():
    assert importlib.util.find_spec("app.backend.infrastructure.repositories.files") is not None
    return importlib.import_module("app.backend.infrastructure.repositories.files")


def _station(station_id: str, n_ports: int = 2) -> dict[str, object]:
    return {
        "station_id": station_id,
        "name": f"Station {station_id}",
        "lat": 10.7,
        "lng": 106.7,
        "n_ports": n_ports,
        "power_kw": 60.0,
        "connector_types": ["CCS2"],
        "network": "synthetic-network",
        "station_type": "urban",
        "source": "synthetic-test-fixture",
        "assumptions": ["test only"],
    }


def _write_stations(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


class TestFileStationRepository(StationRepositoryContract):
    @pytest.fixture(autouse=True)
    def _station_fixture(self, tmp_path: Path) -> None:
        self._path = _write_stations(
            tmp_path / "stations.json", [_station("S002"), _station("S001")]
        )

    def make_repository(self):
        return _files_module().FileStationRepository(self._path)


def _status_row(
    station_id: str,
    ts: datetime,
    scenario: Scenario = Scenario.NORMAL,
    *,
    free: int = 1,
    busy: int = 1,
    broken: int = 0,
) -> dict[str, object]:
    return {
        "station_id": station_id,
        "ts": ts,
        "ports_free": free,
        "ports_busy": busy,
        "ports_broken": broken,
        "scenario": scenario.value,
    }


def _write_statuses(path: Path, rows: list[dict[str, object]]) -> Path:
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def test_file_station_repository_validates_once_orders_and_preserves_provenance(
    tmp_path: Path,
) -> None:
    files = _files_module()
    repository = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S002"), _station("S001")])
    )

    assert isinstance(repository, StationRepository)
    assert [station.station_id for station in repository.list_stations()] == ["S001", "S002"]
    assert repository.get_station("S001").source == "synthetic-test-fixture"
    assert repository.get_station("S001") is repository.get_station("S001")


@pytest.mark.parametrize(
    "rows",
    [
        [_station("S001"), _station("S001")],
        [{**_station("S001"), "n_ports": 0}],
        [{key: value for key, value in _station("S001").items() if key != "source"}],
    ],
)
def test_file_station_repository_rejects_invalid_metadata(
    tmp_path: Path, rows: list[dict[str, object]]
) -> None:
    files = _files_module()
    with pytest.raises((ValueError, ValidationError)):
        files.FileStationRepository(_write_stations(tmp_path / "stations.json", rows))


def test_file_station_repository_uses_typed_errors_for_missing_sources_and_ids(
    tmp_path: Path,
) -> None:
    files = _files_module()
    with pytest.raises(DataSourceUnavailableError):
        files.FileStationRepository(tmp_path / "missing.json")

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(DataSourceUnavailableError):
        files.FileStationRepository(malformed)

    repository = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    with pytest.raises(StationNotFoundError):
        repository.get_station("UNKNOWN")


def test_parquet_status_repository_returns_only_exact_requested_scenario_window(
    tmp_path: Path,
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001"), _station("S002")])
    )
    observed = datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7)
    history = _write_statuses(
        tmp_path / "status.parquet",
        [
            _status_row("S001", observed, Scenario.NORMAL),
            _status_row("S001", observed - timedelta(minutes=15), Scenario.NORMAL),
            _status_row("S001", observed - timedelta(minutes=30), Scenario.NORMAL),
            _status_row("S001", observed + timedelta(minutes=5), Scenario.NORMAL),
            _status_row("S001", observed, Scenario.TET, free=0, busy=2),
            _status_row("S002", observed, Scenario.NORMAL),
        ],
    )
    repository = files.ParquetStatusRepository(history, stations, Scenario.NORMAL)

    result = repository.window("S001", observed, (0, 15, 30))

    assert isinstance(repository, StatusRepository)
    assert result.lags == (0, 15, 30)
    assert [item.ts for item in result.statuses] == [
        observed,
        observed - timedelta(minutes=15),
        observed - timedelta(minutes=30),
    ]
    assert {item.scenario for item in result.statuses} == {Scenario.NORMAL}
    assert all(item.ts <= observed and item.station_id == "S001" for item in result.statuses)


@pytest.mark.parametrize("column", ["station_id", "scenario"])
def test_parquet_status_repository_accepts_dictionary_encoded_text_columns(
    tmp_path: Path, column: str
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    observed = datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7)
    history = tmp_path / "status.parquet"
    frame = pd.DataFrame([_status_row("S001", observed)])
    frame[column] = frame[column].astype("category")
    frame.to_parquet(history, index=False)

    repository = files.ParquetStatusRepository(history, stations, Scenario.NORMAL)

    result = repository.window("S001", observed, (0,))

    assert [(item.station_id, item.scenario, item.ts) for item in result.statuses] == [
        ("S001", Scenario.NORMAL, observed)
    ]


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [_status_row("S001", datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7), free=2, busy=1)],
        [
            _status_row("S001", datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7)),
            _status_row("S001", datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7)),
        ],
    ],
)
def test_parquet_status_repository_rejects_invalid_or_duplicate_selected_statuses(
    tmp_path: Path, rows: list[dict[str, object]]
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    history = _write_statuses(tmp_path / "status.parquet", rows)
    if not rows:
        with pytest.raises(ValueError, match="required columns"):
            files.ParquetStatusRepository(history, stations, Scenario.NORMAL)
    else:
        repository = files.ParquetStatusRepository(history, stations, Scenario.NORMAL)
        with pytest.raises(DataSourceUnavailableError):
            repository.window("S001", datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7), (0,))


def test_parquet_status_repository_invalid_selected_data_maps_to_503(
    tmp_path: Path,
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    observed = datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7)
    history = _write_statuses(
        tmp_path / "status.parquet", [_status_row("S001", observed, free=2, busy=1)]
    )
    repository = files.ParquetStatusRepository(history, stations, Scenario.NORMAL)
    app = FastAPI()
    app.add_exception_handler(DomainError, domain_error_handler)

    @app.get("/status")
    def status() -> object:
        return repository.window("S001", observed, (0,))

    response = TestClient(app, raise_server_exceptions=False).get("/status")

    assert response.status_code == 503
    assert response.json()["code"] == "DATA_SOURCE_UNAVAILABLE"


def test_parquet_status_repository_rejects_unknown_station_missing_snapshot_and_bad_observed_time(
    tmp_path: Path,
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    observed = datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7)
    history = _write_statuses(tmp_path / "status.parquet", [_status_row("S001", observed)])
    repository = files.ParquetStatusRepository(history, stations, Scenario.NORMAL)

    with pytest.raises(StationNotFoundError):
        repository.window("UNKNOWN", observed, (0,))
    with pytest.raises(DataSourceUnavailableError):
        repository.window("S001", observed, (0, 15))
    with pytest.raises(ValueError, match="five-minute"):
        repository.window("S001", observed.replace(minute=1), (0,))
    with pytest.raises(ValueError, match="60"):
        repository.window("S001", observed, (120,))


def test_parquet_status_repository_rejects_unreadable_and_missing_schema_sources(
    tmp_path: Path,
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    broken = tmp_path / "broken.parquet"
    broken.write_bytes(b"not a parquet file")
    with pytest.raises(DataSourceUnavailableError):
        files.ParquetStatusRepository(broken, stations, Scenario.NORMAL)

    missing_schema = _write_statuses(
        tmp_path / "missing-schema.parquet",
        [{"station_id": "S001", "ts": datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7)}],
    )
    with pytest.raises(ValueError, match="required columns"):
        files.ParquetStatusRepository(missing_schema, stations, Scenario.NORMAL)


def test_parquet_status_repository_rejects_wrong_arrow_column_types_at_construction(
    tmp_path: Path,
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    wrong_types = _write_statuses(
        tmp_path / "wrong-types.parquet",
        [
            {
                "station_id": "S001",
                "ts": "2026-10-12T10:00:00+07:00",
                "ports_free": 1.0,
                "ports_busy": 1.0,
                "ports_broken": 0.0,
                "scenario": "normal",
            }
        ],
    )
    with pytest.raises(ValueError, match="invalid schema types"):
        files.ParquetStatusRepository(wrong_types, stations, Scenario.NORMAL)


def test_parquet_status_repository_rejects_directory_with_invalid_fragment_schema(
    tmp_path: Path,
) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    dataset_dir = tmp_path / "status-dataset"
    dataset_dir.mkdir()
    _write_statuses(
        dataset_dir / "a-valid.parquet",
        [_status_row("S001", datetime(2026, 10, 12, 10, 0, tzinfo=UTC_PLUS_7))],
    )
    _write_statuses(
        dataset_dir / "z-invalid.parquet",
        [
            {
                "station_id": "S001",
                "ts": "2026-10-12T10:00:00+07:00",
                "ports_free": 1.0,
                "ports_busy": 1.0,
                "ports_broken": 0.0,
                "scenario": "normal",
            }
        ],
    )

    with pytest.raises(ValueError, match="invalid schema types"):
        files.ParquetStatusRepository(dataset_dir, stations, Scenario.NORMAL)


def test_disappeared_history_bounds_raise_typed_unavailable(tmp_path: Path) -> None:
    files = _files_module()
    stations = files.FileStationRepository(
        _write_stations(tmp_path / "stations.json", [_station("S001")])
    )
    history = _write_statuses(
        tmp_path / "status.parquet",
        [_status_row("S001", datetime(2026, 10, 12, 10, tzinfo=UTC_PLUS_7))],
    )
    repository = files.ParquetStatusRepository(history, stations, Scenario.NORMAL)
    assert repository.bounds()[0] is not None
    history.unlink()
    with pytest.raises(DataSourceUnavailableError, match="history is unavailable"):
        repository.bounds()

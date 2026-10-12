"""Contract checks for canonical station-status training data."""

import json
from pathlib import Path

import pandas as pd
import pytest

from app.backend.contracts.stations import Station
from app.backend.modules.prediction.dataset import load_status_frame, validate_status_frame


@pytest.fixture
def stations() -> tuple[Station, ...]:
    path = Path(__file__).parents[2] / "station_data" / "fixtures" / "stations.json"
    return tuple(Station.model_validate(row) for row in json.loads(path.read_text()))


@pytest.fixture
def valid_frame() -> pd.DataFrame:
    # Intentionally unsorted: validation should return a sorted copy.
    return pd.DataFrame(
        [
            ("S002", "2026-10-13T08:05:00+07:00", 2, 4, 0, "normal"),
            ("S001", "2026-10-13T08:05:00+07:00", 3, 1, 0, "normal"),
            ("S001", "2026-10-13T08:00:00+07:00", 4, 0, 0, "normal"),
            ("S001", "2026-10-13T08:00:00+07:00", 2, 2, 0, "tet"),
        ],
        columns=["station_id", "ts", "ports_free", "ports_busy", "ports_broken", "scenario"],
    )


def test_valid_data_is_sorted_normalized_and_input_is_unchanged(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...]
) -> None:
    original = valid_frame.copy(deep=True)
    result = validate_status_frame(valid_frame, stations)

    pd.testing.assert_frame_equal(valid_frame, original)
    assert result is not valid_frame
    assert list(result.columns) == [
        "station_id",
        "ts",
        "ports_free",
        "ports_busy",
        "ports_broken",
        "scenario",
    ]
    assert list(zip(result["scenario"], result["station_id"], strict=True)) == [
        ("normal", "S001"),
        ("normal", "S001"),
        ("normal", "S002"),
        ("tet", "S001"),
    ]
    assert list(result.loc[result["station_id"] == "S001", "ts"].dt.minute) == [0, 5, 0]
    assert result["ts"].dt.tz is not None
    assert result["ts"].iloc[0].utcoffset().total_seconds() == 7 * 3600


def test_rejects_duplicate_scenario_station_timestamp(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...]
) -> None:
    duplicates = pd.concat([valid_frame, valid_frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="unique|duplicate"):
        validate_status_frame(duplicates, stations)


def test_different_scenarios_may_share_station_and_timestamp(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...]
) -> None:
    assert len(validate_status_frame(valid_frame, stations)) == 4


def test_rejects_capacity_mismatch(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...]
) -> None:
    valid_frame.loc[0, "ports_free"] += 1
    with pytest.raises(ValueError, match="capacity"):
        validate_status_frame(valid_frame, stations)


@pytest.mark.parametrize("bad_value", [-1, 1.5, None, "two", True])
def test_rejects_invalid_count_values(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...], bad_value: object
) -> None:
    valid_frame["ports_busy"] = valid_frame["ports_busy"].astype(object)
    valid_frame.at[0, "ports_busy"] = bad_value
    with pytest.raises(ValueError, match="ports_busy"):
        validate_status_frame(valid_frame, stations)


@pytest.mark.parametrize("missing", ["ts", "scenario", "ports_free", "station_id"])
def test_rejects_missing_columns(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...], missing: str
) -> None:
    with pytest.raises(ValueError, match="columns"):
        validate_status_frame(valid_frame.drop(columns=missing), stations)


def test_rejects_extra_columns(valid_frame: pd.DataFrame, stations: tuple[Station, ...]) -> None:
    valid_frame["unexpected"] = 1
    with pytest.raises(ValueError, match="columns"):
        validate_status_frame(valid_frame, stations)


@pytest.mark.parametrize("station_id", ["S404", "", None, 123])
def test_rejects_invalid_station_ids(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...], station_id: object
) -> None:
    valid_frame["station_id"] = valid_frame["station_id"].astype(object)
    valid_frame.at[0, "station_id"] = station_id
    with pytest.raises(ValueError, match="station_id"):
        validate_status_frame(valid_frame, stations)


@pytest.mark.parametrize("scenario", ["busy", "NORMAL", None, 1])
def test_rejects_unknown_scenario(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...], scenario: object
) -> None:
    valid_frame["scenario"] = valid_frame["scenario"].astype(object)
    valid_frame.at[0, "scenario"] = scenario
    with pytest.raises(ValueError, match="scenario"):
        validate_status_frame(valid_frame, stations)


@pytest.mark.parametrize(
    "ts",
    [
        "2026-10-13T08:00:00",  # missing timezone
        "2026-10-13T08:00:00Z",  # UTC is not the canonical +07 offset
        "2026-10-13T08:00:00+08:00",
        "2026-10-13T08:03:00+07:00",  # not a five-minute boundary
        "2026-10-13T08:00:01+07:00",
        "not-a-date",
        None,
    ],
)
def test_rejects_invalid_timestamps(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...], ts: object
) -> None:
    valid_frame["ts"] = valid_frame["ts"].astype(object)
    valid_frame.at[0, "ts"] = ts
    with pytest.raises(ValueError, match="ts"):
        validate_status_frame(valid_frame, stations)


def test_rejects_duplicate_station_metadata(
    valid_frame: pd.DataFrame, stations: tuple[Station, ...]
) -> None:
    with pytest.raises(ValueError, match="station_id"):
        validate_status_frame(valid_frame, (*stations, stations[0]))


def test_rejects_empty_data(stations: tuple[Station, ...], valid_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_status_frame(valid_frame.iloc[0:0], stations)


@pytest.mark.parametrize("extension", ["csv", "parquet"])
def test_file_loader_roundtrip(
    tmp_path: Path, valid_frame: pd.DataFrame, stations: tuple[Station, ...], extension: str
) -> None:
    path = tmp_path / f"station_status.{extension}"
    if extension == "csv":
        valid_frame.to_csv(path, index=False)
    else:
        valid_frame.to_parquet(path, index=False)

    loaded = load_status_frame(path)
    result = validate_status_frame(loaded, stations)
    assert len(result) == len(valid_frame)
    assert result["ts"].dt.tz is not None


def test_file_loader_preserves_string_station_id(tmp_path: Path) -> None:
    path = tmp_path / "station_status.csv"
    path.write_text(
        "station_id,ts,ports_free,ports_busy,ports_broken,scenario\n"
        "001,2026-10-13T08:00:00+07:00,2,0,0,normal\n"
    )
    assert load_status_frame(path).iloc[0]["station_id"] == "001"


def test_file_loader_rejects_unsupported_suffix(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="format|extension|CSV|Parquet"):
        load_status_frame(tmp_path / "station_status.json")

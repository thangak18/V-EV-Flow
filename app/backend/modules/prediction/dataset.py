"""Load and validate the canonical five-minute station-status time series.

Input fields come from docs/DATA_CONTRACT.md. Station capacities are read
from the shared Station contract; they do not belong in station_status files.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from app.backend.contracts.enums import Scenario
from app.backend.contracts.stations import Station

STATUS_COLUMNS = (
    "station_id",
    "ts",
    "ports_free",
    "ports_busy",
    "ports_broken",
    "scenario",
)
COUNT_COLUMNS = ("ports_free", "ports_busy", "ports_broken")
KEY_COLUMNS = ("scenario", "station_id", "ts")
_CANONICAL_OFFSET = timedelta(hours=7)
_SCENARIOS = frozenset(item.value for item in Scenario)


def load_status_frame(path: Path) -> pd.DataFrame:
    """Read raw simulator histories from CSV or Parquet, without altering rows.

    Use ``validate_status_frame`` with station metadata before training.
    IDs remain strings (including numeric IDs with leading zeroes).
    """
    source = Path(path)
    if source.suffix.lower() == ".csv":
        return pd.read_csv(source, dtype={"station_id": "string", "scenario": "string"})
    if source.suffix.lower() == ".parquet":
        return pd.read_parquet(source)
    raise ValueError("Unsupported station-status format; expected CSV or Parquet")


def _is_nonnegative_int(value: object) -> bool:
    return bool(
        isinstance(value, (int, np.integer))
        and not isinstance(value, (bool, np.bool_))
        and value >= 0
    )


def _parse_canonical_time(value: object, row: int) -> pd.Timestamp:
    if not isinstance(value, (str, pd.Timestamp, datetime)):
        raise ValueError(f"ts at row {row} must be an ISO 8601 timestamp")
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"ts at row {row} is not a valid timestamp") from exc

    if not isinstance(timestamp, pd.Timestamp):
        raise ValueError(f"ts at row {row} is not a valid timestamp")
    if timestamp.tzinfo is None or timestamp.utcoffset() != _CANONICAL_OFFSET:
        raise ValueError(f"ts at row {row} must use the +07:00 timezone offset")
    if timestamp.minute % 5 or timestamp.second or timestamp.microsecond or timestamp.nanosecond:
        raise ValueError(f"ts at row {row} must align to a five-minute boundary")
    return timestamp


def validate_status_frame(frame: pd.DataFrame, stations: Sequence[Station]) -> pd.DataFrame:
    """Return a new, chronologically sorted, schema-valid status DataFrame.

    Reject unknown stations, non-integer or inconsistent port counts, bad
    scenarios, noncanonical timestamps, and duplicate scenario/station/time keys.
    Caller-owned frames and station objects are never mutated.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("station_status must be a pandas DataFrame")
    if len(frame.columns) != len(STATUS_COLUMNS) or set(frame.columns) != set(STATUS_COLUMNS):
        raise ValueError(f"station_status columns must be exactly {list(STATUS_COLUMNS)}")
    if frame.empty:
        raise ValueError("station_status is empty")

    capacities: dict[str, int] = {}
    for station in stations:
        if station.station_id in capacities:
            raise ValueError(f"duplicate station_id in metadata: {station.station_id}")
        capacities[station.station_id] = station.n_ports
    if not capacities:
        raise ValueError("station metadata is empty")

    normalized = frame.loc[:, list(STATUS_COLUMNS)].copy(deep=True).reset_index(drop=True)
    for row, station_id in enumerate(normalized["station_id"]):
        if not isinstance(station_id, str) or not station_id.strip():
            raise ValueError(f"invalid station_id at row {row}")
        if station_id not in capacities:
            raise ValueError(f"unknown station_id at row {row}: {station_id}")

    for row, scenario in enumerate(normalized["scenario"]):
        if not isinstance(scenario, str) or scenario not in _SCENARIOS:
            raise ValueError(f"invalid scenario at row {row}: {scenario}")

    for column in COUNT_COLUMNS:
        for row, value in enumerate(normalized[column]):
            if not _is_nonnegative_int(value):
                raise ValueError(f"{column} at row {row} must be a nonnegative integer")
        normalized[column] = normalized[column].astype("int64")

    expected_capacity = normalized["station_id"].map(capacities)
    observed_capacity = normalized.loc[:, list(COUNT_COLUMNS)].sum(axis=1)
    if (observed_capacity != expected_capacity).any():
        raise ValueError("port counts do not match station capacity")

    normalized["ts"] = pd.DatetimeIndex(
        [_parse_canonical_time(value, row) for row, value in enumerate(normalized["ts"])]
    )
    if normalized.duplicated(subset=list(KEY_COLUMNS)).any():
        raise ValueError("station_status keys (scenario, station_id, ts) must be unique")

    return normalized.sort_values(list(KEY_COLUMNS), kind="mergesort").reset_index(drop=True)

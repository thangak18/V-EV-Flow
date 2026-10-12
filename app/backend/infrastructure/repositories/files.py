"""File-backed station and status repositories.

The status port has no scenario argument.  This adapter is therefore scoped to
one immutable scenario at construction; composition selects the appropriate
instance rather than using mutable request-global state.
"""

import json
from datetime import datetime, timedelta
from numbers import Integral
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.types as pa_types
from pydantic import ValidationError

from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import DataSourceUnavailableError, StationNotFoundError
from app.backend.contracts.ports import StationRepository
from app.backend.contracts.recommendation import StatusWindow
from app.backend.contracts.stations import Station, StationStatus

_CANONICAL_OFFSET = timedelta(hours=7)
_STATUS_COLUMNS = (
    "station_id",
    "ts",
    "ports_free",
    "ports_busy",
    "ports_broken",
    "scenario",
)
_STATUS_KEY_COLUMNS = ("scenario", "station_id", "ts")


class FileStationRepository:
    """Eagerly validate station metadata once and serve it from an ID index."""

    def __init__(self, path: Path) -> None:
        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DataSourceUnavailableError(f"unable to read station metadata: {source}") from exc
        if not isinstance(payload, list):
            raise ValueError("station metadata must be a JSON array")
        try:
            stations = tuple(Station.model_validate(row) for row in payload)
        except ValidationError:
            raise
        if not stations:
            raise ValueError("station metadata is empty")
        by_id = {station.station_id: station for station in stations}
        if len(by_id) != len(stations):
            raise ValueError("station metadata contains duplicate station_id values")
        self._stations = tuple(sorted(stations, key=lambda station: station.station_id))
        self._by_id = by_id

    def list_stations(self) -> tuple[Station, ...]:
        return self._stations

    def get_station(self, station_id: str) -> Station:
        try:
            return self._by_id[station_id]
        except KeyError as exc:
            raise StationNotFoundError(f"unknown station: {station_id}") from exc


class ParquetStatusRepository:
    """Read bounded, scenario-scoped Parquet status windows on demand."""

    def __init__(
        self,
        path: Path,
        station_repository: StationRepository,
        scenario: Scenario,
    ) -> None:
        self._path = Path(path)
        self._stations = station_repository
        self._scenario = Scenario(scenario)
        try:
            self._dataset = ds.dataset(self._path, format="parquet")
        except (OSError, ValueError, TypeError) as exc:
            raise DataSourceUnavailableError(f"unable to open status data: {self._path}") from exc
        self._validate_schema_types()

    def window(
        self,
        station_id: str,
        observed_at: datetime,
        lags: tuple[int, ...] = (15, 30, 60),
    ) -> StatusWindow:
        station = self._stations.get_station(station_id)
        self._validate_window_request(observed_at, lags)
        expected = tuple(observed_at - timedelta(minutes=lag) for lag in lags)
        earliest = min(expected)
        expression = (
            (ds.field("station_id") == station_id)
            & (ds.field("scenario") == self._scenario.value)
            & (ds.field("ts") >= earliest)
            & (ds.field("ts") <= observed_at)
        )
        try:
            table = self._dataset.to_table(filter=expression, columns=list(_STATUS_COLUMNS))
            frame = table.to_pandas()
        except Exception as exc:  # pyarrow exception hierarchy varies by source/backend
            raise DataSourceUnavailableError(f"unable to read status data: {self._path}") from exc
        if frame.empty:
            raise DataSourceUnavailableError(
                f"no {self._scenario.value} status data for {station_id} in requested window"
            )

        try:
            normalized = self._validate_rows(frame, station)
        except ValueError as exc:
            raise DataSourceUnavailableError(f"invalid status data: {self._path}") from exc
        records: dict[datetime, dict[str, object]] = {}
        for row in normalized.to_dict(orient="records"):
            timestamp = row["ts"]
            if not isinstance(timestamp, datetime):
                raise DataSourceUnavailableError("status data contains an invalid timestamp")
            records[timestamp] = row
        missing = [timestamp for timestamp in expected if timestamp not in records]
        if missing:
            raise DataSourceUnavailableError(
                f"missing status snapshots for {station_id}: "
                + ", ".join(timestamp.isoformat() for timestamp in missing)
            )
        statuses = tuple(
            StationStatus(
                station_id=station_id,
                ts=timestamp,
                ports_free=_count(records[timestamp], "ports_free"),
                ports_busy=_count(records[timestamp], "ports_busy"),
                ports_broken=_count(records[timestamp], "ports_broken"),
                n_ports=station.n_ports,
                scenario=self._scenario,
            )
            for timestamp in expected
        )
        return StatusWindow(
            station_id=station_id,
            observed_at=observed_at,
            lags=lags,
            statuses=statuses,
        )

    @staticmethod
    def _validate_window_request(observed_at: datetime, lags: tuple[int, ...]) -> None:
        if observed_at.tzinfo is None or observed_at.utcoffset() != _CANONICAL_OFFSET:
            raise ValueError("observed_at must use the +07:00 timezone offset")
        if observed_at.minute % 5 or observed_at.second or observed_at.microsecond:
            raise ValueError("observed_at must align to a five-minute boundary")
        if not lags or any(
            not isinstance(lag, int) or isinstance(lag, bool) or not 0 <= lag <= 60 for lag in lags
        ):
            raise ValueError("lags must be non-empty integer minutes between 0 and 60")

    def _validate_schema_types(self) -> None:
        schemas = [self._dataset.schema]
        try:
            schemas.extend(fragment.physical_schema for fragment in self._dataset.get_fragments())
        except Exception as exc:  # pyarrow fragment metadata errors vary by filesystem/backend
            raise DataSourceUnavailableError(
                f"unable to inspect status data: {self._path}"
            ) from exc

        missing: set[str] = set()
        invalid: set[str] = set()
        for schema in schemas:
            missing.update(set(_STATUS_COLUMNS).difference(schema.names))
            if missing:
                continue
            invalid.update(self._invalid_schema_type_fields(schema))
        if missing:
            raise ValueError(f"status data is missing required columns: {sorted(missing)}")
        if invalid:
            raise ValueError(f"status data has invalid schema types: {sorted(invalid)}")

    @staticmethod
    def _invalid_schema_type_fields(schema) -> set[str]:
        text_fields = ("station_id", "scenario")
        count_fields = ("ports_free", "ports_busy", "ports_broken")
        invalid = {
            name
            for name in text_fields
            if not ParquetStatusRepository._is_text_type(schema.field(name).type)
        }
        invalid.update(
            name for name in count_fields if not pa_types.is_integer(schema.field(name).type)
        )
        timestamp_type = schema.field("ts").type
        if not pa_types.is_timestamp(timestamp_type) or timestamp_type.tz is None:
            invalid.add("ts")
        return invalid

    @staticmethod
    def _is_text_type(data_type: pa.DataType) -> bool:
        """Accept Arrow strings and dictionary-encoded string columns only."""
        if pa_types.is_string(data_type) or pa_types.is_large_string(data_type):
            return True
        return bool(
            pa_types.is_dictionary(data_type)
            and ParquetStatusRepository._is_text_type(data_type.value_type)
        )

    def _validate_rows(self, frame: pd.DataFrame, station: Station) -> pd.DataFrame:
        """Validate only the predicate-selected rows; never materialize full history."""
        if set(frame.columns) != set(_STATUS_COLUMNS):
            raise ValueError(f"status data columns must be exactly {list(_STATUS_COLUMNS)}")
        if frame.duplicated(subset=list(_STATUS_KEY_COLUMNS)).any():
            raise ValueError("status data contains duplicate scenario/station/timestamp keys")
        validated: list[dict[str, object]] = []
        for row in frame.loc[:, list(_STATUS_COLUMNS)].to_dict(orient="records"):
            if row["station_id"] != station.station_id:
                raise ValueError("status data station_id does not match request")
            if row["scenario"] != self._scenario.value:
                raise ValueError("status data scenario does not match repository scope")
            timestamp = row["ts"]
            if not isinstance(timestamp, datetime):
                raise ValueError("status data contains an invalid timestamp")
            if timestamp.utcoffset() != _CANONICAL_OFFSET:
                raise ValueError("status timestamps must use the +07:00 timezone offset")
            if timestamp.minute % 5 or timestamp.second or timestamp.microsecond:
                raise ValueError("status timestamps must align to five-minute boundaries")
            counts = tuple(row[name] for name in ("ports_free", "ports_busy", "ports_broken"))
            if any(
                not isinstance(value, Integral) or isinstance(value, bool) or value < 0
                for value in counts
            ):
                raise ValueError("status port counts must be nonnegative integers")
            if sum(counts) != station.n_ports:
                raise ValueError("status port counts must match station capacity")
            validated.append(row)
        return pd.DataFrame(validated).sort_values(list(_STATUS_KEY_COLUMNS), kind="mergesort")


def _count(row: dict[str, object], name: str) -> int:
    value = row[name]
    if not isinstance(value, int) or isinstance(value, bool):
        raise DataSourceUnavailableError(f"status data contains an invalid {name} value")
    return value

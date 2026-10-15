"""Canonical authenticated partner feed storage, not a vendor-specific translator.

Only callers with the ingestion credential may assert measured occupancy.
Unknown/ambiguous provider status categories must be resolved by the partner,
never mapped to broken ports automatically. Receipt of data is not independent
verification of its truth and does not establish real-world model accuracy.
"""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import DataSourceUnavailableError, RequestConflictError
from app.backend.contracts.ports import StationRepository
from app.backend.contracts.recommendation import StatusWindow
from app.backend.contracts.runtime import SnapshotBatch
from app.backend.contracts.stations import StationStatus


class PartnerHistory:
    def __init__(self, path: Path, stations: StationRepository, source: str) -> None:
        self.path, self.stations, self.source = Path(path), stations, source
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS provenance (source TEXT, stations_hash TEXT)")
            fingerprint = hashlib.sha256(
                json.dumps(
                    [station.model_dump(mode="json") for station in stations.list_stations()],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            provenance = db.execute("SELECT source,stations_hash FROM provenance").fetchone()
            if provenance and provenance != (source, fingerprint):
                raise ValueError(
                    "partner history belongs to another source or station configuration"
                )
            if not provenance:
                db.execute("INSERT INTO provenance VALUES (?,?)", (source, fingerprint))
            db.execute(
                "CREATE TABLE IF NOT EXISTS snapshots (station TEXT, scenario TEXT, "
                "ts TEXT, free INTEGER, busy INTEGER, broken INTEGER, "
                "PRIMARY KEY(station,scenario,ts))"
            )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def ingest(self, batch: SnapshotBatch) -> int:
        now = datetime.now(UTC)
        for row in batch.snapshots:
            station = self.stations.get_station(row.station_id)
            if row.n_ports != station.n_ports or len(station.connector_types) != 1:
                raise ValueError("snapshot capacity/connector metadata is incompatible")
            if (
                row.ts.utcoffset() != timedelta(hours=7)
                or row.ts.minute % 5
                or row.ts.second
                or row.ts.microsecond
                or row.ts > now
            ):
                raise ValueError("snapshot must be an observed +07 five-minute bucket, not future")
            if row.scenario != Scenario.NORMAL:
                raise ValueError(
                    "measured feed accepts normal only, never simulated demand scenarios"
                )
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for row in batch.snapshots:
                key = (row.station_id, row.scenario.value, row.ts.isoformat())
                counts = (row.ports_free, row.ports_busy, row.ports_broken)
                existing = db.execute(
                    "SELECT free,busy,broken FROM snapshots "
                    "WHERE station=? AND scenario=? AND ts=?",
                    key,
                ).fetchone()
                if existing is not None and existing != counts:
                    raise RequestConflictError("existing partner snapshot cannot be overwritten")
                db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?)", (*key, *counts))
        return len(batch.snapshots)

    def bounds(self, scenario: Scenario) -> tuple[datetime | None, datetime | None]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT ts FROM snapshots WHERE scenario=? GROUP BY ts "
                "HAVING COUNT(DISTINCT station)=? ORDER BY ts",
                (scenario.value, len(self.stations.list_stations())),
            ).fetchall()
        return (
            (None, None)
            if not rows
            else (datetime.fromisoformat(rows[0][0]), datetime.fromisoformat(rows[-1][0]))
        )


class PartnerStatusRepository:
    def __init__(self, history: PartnerHistory, scenario: Scenario) -> None:
        self.history, self.scenario = history, scenario

    def window(
        self, station_id: str, observed_at: datetime, lags: tuple[int, ...] = (15, 30, 60)
    ) -> StatusWindow:
        from app.backend.infrastructure.repositories.files import ParquetStatusRepository

        ParquetStatusRepository._validate_window_request(observed_at, lags)
        station = self.history.stations.get_station(station_id)
        if observed_at > datetime.now(UTC):
            raise DataSourceUnavailableError("future live observations are unavailable")
        with self.history.connect() as db:
            rows = {
                datetime.fromisoformat(row[0]): row[1:]
                for row in db.execute(
                    "SELECT ts,free,busy,broken FROM snapshots "
                    "WHERE station=? AND scenario=? AND ts>=? AND ts<=?",
                    (
                        station_id,
                        self.scenario.value,
                        (observed_at - timedelta(minutes=max(lags))).isoformat(),
                        observed_at.isoformat(),
                    ),
                )
            }
        if observed_at not in rows:
            raise DataSourceUnavailableError("current partner snapshot is unavailable")
        statuses = tuple(
            StationStatus(
                station_id=station_id,
                ts=ts,
                ports_free=rows[ts][0],
                ports_busy=rows[ts][1],
                ports_broken=rows[ts][2],
                n_ports=station.n_ports,
                scenario=self.scenario,
            )
            for lag in lags
            if (ts := observed_at - timedelta(minutes=lag)) in rows
        )
        return StatusWindow(
            station_id=station_id, observed_at=observed_at, lags=lags, statuses=statuses
        )

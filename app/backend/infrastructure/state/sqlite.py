"""Durable expected-demand receipts with SQLite transactions across workers.

The decision transaction spans read/route/predict/commit. This deliberately
serializes decisions across processes on one host. SQLite is not a distributed
booking system and must reside on a local disk, not NFS or several replicas.
"""

import asyncio
import json
import sqlite3
from collections.abc import Callable, Mapping
from contextlib import closing
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import isfinite
from pathlib import Path
from types import MappingProxyType

from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import RequestConflictError
from app.backend.contracts.recommendation import RecommendationResult
from app.backend.infrastructure.state.virtual_load import VirtualLoadStore
from app.backend.modules.recommendation.allocation import (
    AllocationReceipt,
    Reservation,
    bucket_start,
)


class _DecisionLock(asyncio.Lock):
    def __init__(self, owner: "SQLiteVirtualLoadStore") -> None:
        super().__init__()
        self.owner = owner

    async def __aenter__(self) -> None:
        await self.acquire()
        connection = None
        try:
            connection = self.owner._connect()
            # Nonblocking retries keep a second worker from blocking its event loop.
            deadline = asyncio.get_running_loop().time() + 120
            while True:
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    break
                except sqlite3.OperationalError as exc:
                    if (
                        "locked" not in str(exc).lower()
                        or asyncio.get_running_loop().time() >= deadline
                    ):
                        raise
                    await asyncio.sleep(0.025)
            self.owner._current.set(connection)
        except BaseException:
            if connection is not None:
                connection.close()
            self.release()
            raise

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        connection = self.owner._current.get()
        try:
            if connection is not None:
                connection.rollback() if exc_type else connection.commit()
        finally:
            self.owner._current.set(None)
            if connection is not None:
                connection.close()
            self.release()


class SQLiteVirtualLoadStore:
    def __init__(
        self,
        path: Path,
        *,
        ttl: timedelta = timedelta(minutes=30),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if ttl <= timedelta(0):
            raise ValueError("receipt TTL must be positive")
        self.path, self.ttl, self.clock = Path(path), ttl, clock
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.touch(mode=0o600, exist_ok=True)
        self._current: ContextVar[sqlite3.Connection | None] = ContextVar(
            f"allocation-transaction-{id(self)}", default=None
        )
        self._lock = _DecisionLock(self)
        with closing(self._connect(timeout=5)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS receipts (
                  id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL,
                  reservation TEXT, created TEXT NOT NULL, expires TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS loads (
                  receipt TEXT REFERENCES receipts(id) ON DELETE CASCADE,
                  scenario TEXT, station TEXT, bucket TEXT, amount TEXT,
                  PRIMARY KEY(receipt,scenario,station,bucket));
                CREATE INDEX IF NOT EXISTS load_bucket ON loads(scenario,bucket);
            """)

    @property
    def decision_lock(self) -> asyncio.Lock:
        return self._lock

    def _connect(self, timeout: float = 0) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=timeout, isolation_level=None)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _db(self) -> sqlite3.Connection:
        db = self._current.get()
        if db is None:
            raise RuntimeError("SQLite allocation operations require a decision transaction")
        now = self.clock()
        if now.utcoffset() is None:
            raise ValueError("processing clock must be aware")
        db.execute("DELETE FROM receipts WHERE expires<=?", (now.astimezone(UTC).isoformat(),))
        return db

    @staticmethod
    def _decode(row) -> AllocationReceipt:
        data = json.loads(row[3]) if row[3] else None
        reservation = (
            None
            if data is None
            else Reservation(
                Scenario(data["scenario"]),
                data["station_id"],
                datetime.fromisoformat(data["eta"]),
                data["charge_duration_minutes"],
                data["expected_load"],
            )
        )
        return AllocationReceipt(
            row[0],
            row[1],
            row[2],
            reservation,
            datetime.fromisoformat(row[4]),
            datetime.fromisoformat(row[5]),
        )

    async def lookup(self, request_id: str, payload_hash: str) -> AllocationReceipt | None:
        if self._current.get() is None:
            async with self.decision_lock:
                return await self.lookup(request_id, payload_hash)
        row = self._db().execute("SELECT * FROM receipts WHERE id=?", (request_id,)).fetchone()
        if row is None:
            return None
        if row[1] != payload_hash:
            raise RequestConflictError(f"request_id already exists: {request_id}")
        return self._decode(row)

    async def snapshot(self, at: datetime, scenario: Scenario) -> Mapping[str, float]:
        if self._current.get() is None:
            async with self.decision_lock:
                return await self.snapshot(at, scenario)
        bucket = bucket_start(at)
        totals: dict[str, Decimal] = {}
        for station, amount in self._db().execute(
            "SELECT station,amount FROM loads WHERE scenario=? AND bucket=?",
            (Scenario(scenario).value, bucket.isoformat()),
        ):
            totals[station] = totals.get(station, Decimal(0)) + Decimal(amount)
        return MappingProxyType({station: float(value) for station, value in totals.items()})

    async def reserve(
        self,
        request_id: str,
        payload_hash: str,
        result: RecommendationResult,
        reservation: Reservation | None,
    ) -> AllocationReceipt:
        if self._current.get() is None:
            async with self.decision_lock:
                return await self.reserve(request_id, payload_hash, result, reservation)
        existing = await self.lookup(request_id, payload_hash)
        if existing:
            return existing
        # Reuse the canonical in-memory adapter's receipt/plan consistency checks.
        now = self.clock().astimezone(UTC)
        validator = VirtualLoadStore(ttl=self.ttl, clock=lambda: now)
        receipt = await validator.reserve(request_id, payload_hash, result, reservation)
        data = (
            None
            if reservation is None
            else {
                "scenario": reservation.scenario.value,
                "station_id": reservation.station_id,
                "eta": reservation.eta.isoformat(),
                "charge_duration_minutes": reservation.charge_duration_minutes,
                "expected_load": reservation.expected_load,
            }
        )
        db = self._db()
        if reservation is not None:
            for at in reservation.buckets():
                loads = await self.snapshot(at, reservation.scenario)
                if not isfinite(loads.get(reservation.station_id, 0) + reservation.expected_load):
                    raise ValueError("virtual load overflow")
        db.execute(
            "INSERT INTO receipts VALUES (?,?,?,?,?,?)",
            (
                request_id,
                payload_hash,
                receipt.result_json,
                json.dumps(data) if data else None,
                receipt.created_at.isoformat(),
                receipt.expires_at.isoformat(),
            ),
        )
        if reservation is not None and reservation.expected_load:
            db.executemany(
                "INSERT INTO loads VALUES (?,?,?,?,?)",
                [
                    (
                        request_id,
                        reservation.scenario.value,
                        reservation.station_id,
                        at.isoformat(),
                        str(Decimal(str(reservation.expected_load))),
                    )
                    for at in reservation.buckets()
                ],
            )
        return receipt

    async def reset(self) -> None:
        if self._current.get() is None:
            async with self.decision_lock:
                await self.reset()
                return
        self._db().execute("DELETE FROM receipts")

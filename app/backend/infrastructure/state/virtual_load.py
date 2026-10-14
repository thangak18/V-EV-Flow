"""Single-process expected-demand store with immutable replay and processing TTL.

decision lock -> state lock is the only nested lock order. Independent
reset waits for active decisions before clearing all state. Direct reserve
is counter-atomic, but Driver callers must use AllocationCoordinator for
demand-aware decisions. Expiry removes each receipt's own contribution;
charging duration and receipt retention are independent assumptions.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import isfinite
from types import MappingProxyType

from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import RequestConflictError
from app.backend.contracts.recommendation import RecommendationResult
from app.backend.modules.recommendation import (
    AllocationReceipt,
    Reservation,
    bucket_start,
)

BucketKey = tuple[Scenario, str, datetime]


class VirtualLoadStore:
    """Snapshots are allocated expected demand, not ports_free or ML probability."""

    def __init__(
        self,
        *,
        ttl: timedelta = timedelta(minutes=30),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not isinstance(ttl, timedelta) or ttl <= timedelta(0):
            raise ValueError("receipt TTL must be a positive timedelta")
        self._ttl = ttl
        self._clock = clock
        self._decision_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()
        self._receipts: dict[str, AllocationReceipt] = {}
        self._buckets: dict[BucketKey, dict[str, Decimal]] = {}

    @property
    def decision_lock(self) -> asyncio.Lock:
        return self._decision_lock

    def _now(self) -> datetime:
        now = self._clock()
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise ValueError("processing clock must return an aware datetime")
        return now

    def _prune(self, now: datetime) -> None:
        expired = [receipt for receipt in self._receipts.values() if receipt.expires_at <= now]
        for receipt in expired:
            reservation = receipt.reservation
            if reservation is not None:
                for at in reservation.buckets():
                    key = (reservation.scenario, reservation.station_id, at)
                    contributions = self._buckets.get(key)
                    if contributions is not None:
                        contributions.pop(receipt.request_id, None)
                        if not contributions:
                            del self._buckets[key]
            del self._receipts[receipt.request_id]

    def _lookup(self, request_id: str, payload_hash: str) -> AllocationReceipt | None:
        receipt = self._receipts.get(request_id)
        if receipt is not None and receipt.payload_hash != payload_hash:
            raise RequestConflictError("request_id was already used with a different payload")
        return receipt

    async def lookup(self, request_id: str, payload_hash: str) -> AllocationReceipt | None:
        async with self._state_lock:
            self._prune(self._now())
            return self._lookup(request_id, payload_hash)

    async def reserve(
        self,
        request_id: str,
        payload_hash: str,
        result: RecommendationResult,
        reservation: Reservation | None,
    ) -> AllocationReceipt:
        async with self._state_lock:
            now = self._now()
            self._prune(now)
            existing = self._lookup(request_id, payload_hash)
            if existing is not None:
                return existing
            if not isinstance(request_id, str) or not request_id.strip() or not payload_hash:
                raise ValueError("request_id and payload_hash must be nonempty")
            validated = RecommendationResult.model_validate(
                result.model_dump(mode="python", warnings=False)
            )
            result_json = json.dumps(
                validated.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            if validated.request_id != request_id:
                raise ValueError("result request_id must match receipt request_id")
            if (validated.primary is None) != (reservation is None):
                raise ValueError("only a primary plan may have a reservation")
            keys: tuple[BucketKey, ...] = ()
            contribution = Decimal(0)
            if reservation is not None:
                reservation = Reservation(
                    reservation.scenario,
                    reservation.station_id,
                    reservation.eta,
                    reservation.charge_duration_minutes,
                    reservation.expected_load,
                )
                primary = validated.primary
                if primary is None or (primary.station_id, primary.eta) != (
                    reservation.station_id,
                    reservation.eta,
                ):
                    raise ValueError("reservation must match the selected primary")
                keys = tuple(
                    (reservation.scenario, reservation.station_id, at)
                    for at in reservation.buckets()
                )
                contribution = Decimal(str(reservation.expected_load))
                for key in keys:
                    total = sum(self._buckets.get(key, {}).values(), Decimal(0)) + contribution
                    if not isfinite(float(total)):
                        raise ValueError("virtual load overflow")
            try:
                expires_at = now + self._ttl
            except OverflowError:
                raise ValueError("receipt expiry exceeds the datetime range") from None
            receipt = AllocationReceipt(
                request_id,
                payload_hash,
                result_json,
                reservation,
                now,
                expires_at,
            )
            for key in keys:
                if contribution:
                    self._buckets.setdefault(key, {})[request_id] = contribution
            self._receipts[request_id] = receipt
            return receipt

    async def snapshot(self, at: datetime, scenario: Scenario) -> Mapping[str, float]:
        at = bucket_start(at)
        scenario = Scenario(scenario)
        async with self._state_lock:
            self._prune(self._now())
            snapshot = {
                station_id: float(sum(contributions.values(), Decimal(0)))
                for (namespace, station_id, bucket), contributions in self._buckets.items()
                if namespace == scenario and bucket == at
            }
            return MappingProxyType(snapshot)

    async def reset(self) -> None:
        async with self._decision_lock:
            async with self._state_lock:
                self._receipts.clear()
                self._buckets.clear()

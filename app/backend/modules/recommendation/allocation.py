"""Internal allocation ports, immutable receipts and serialized Driver decisions.

Lock order is shared decision lock then store state lock. Routing/inference run
under the decision lock only. The synchronous strategy has no Driver state or
fallback evidence; its injected measurements must come from verified routing.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from types import MappingProxyType
from typing import Protocol

from app.backend.contracts.enums import Scenario
from app.backend.contracts.recommendation import (
    AllocationContext,
    RankedPlan,
    RecommendationRequest,
    RecommendationResult,
)

from .ranking import RankingConfig, RankingInput, rank_candidates
from .service import VirtualLoadReader

BUCKET_MINUTES = 5
MAX_RESERVATION_BUCKETS = 288
MAX_RESERVATION_DURATION_MINUTES = BUCKET_MINUTES * MAX_RESERVATION_BUCKETS


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validated_request(request: RecommendationRequest) -> RecommendationRequest:
    payload = request.model_dump(mode="json")
    _canonical_json(payload)
    return RecommendationRequest.model_validate(payload)


def canonical_payload_hash(request: RecommendationRequest) -> str:
    """Revalidate mutable input; hash the entire validated JSON-mode payload."""
    validated = _validated_request(request)
    return hashlib.sha256(_canonical_json(validated.model_dump(mode="json")).encode()).hexdigest()


def _number(value: float, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"{name} must be a finite number") from None
    if not isfinite(number) or number < 0 or (positive and number == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return number


def _reservation_duration(value: float) -> float:
    duration = _number(value, "charge_duration_minutes", positive=True)
    if duration > MAX_RESERVATION_DURATION_MINUTES:
        raise ValueError(
            "charge_duration_minutes must span at most "
            f"{MAX_RESERVATION_BUCKETS} five-minute buckets"
        )
    return duration


def bucket_start(at: datetime, *, aligned: bool = False) -> datetime:
    """Floor within the fixed +07 five-minute grid; never shift into the future."""
    if not isinstance(at, datetime) or at.utcoffset() != timedelta(hours=7):
        raise ValueError("time must be timezone-aware with +07:00 offset")
    floored = at.replace(minute=at.minute // 5 * 5, second=0, microsecond=0)
    if aligned and at != floored:
        raise ValueError("ETA must be aligned to the five-minute grid")
    return floored


@dataclass(frozen=True)
class Reservation:
    """Expected primary demand, not occupancy or a physical charging booking."""

    scenario: Scenario
    station_id: str
    eta: datetime
    charge_duration_minutes: float
    expected_load: float = 1.0

    def __post_init__(self) -> None:
        Scenario(self.scenario)
        if not isinstance(self.station_id, str) or not self.station_id.strip():
            raise ValueError("station_id must be nonempty")
        bucket_start(self.eta, aligned=True)
        duration = _reservation_duration(self.charge_duration_minutes)
        _number(self.expected_load, "expected_load")
        try:
            end = self.eta + timedelta(minutes=duration)
        except (OverflowError, ValueError):
            raise ValueError("charging duration exceeds the datetime range") from None
        if end <= self.eta:
            raise ValueError("charging duration must advance ETA")

    def buckets(self) -> tuple[datetime, ...]:
        end = self.eta + timedelta(minutes=self.charge_duration_minutes)
        current = self.eta
        buckets = []
        while current < end:
            buckets.append(current)
            if end - current <= timedelta(minutes=BUCKET_MINUTES):
                break
            current += timedelta(minutes=BUCKET_MINUTES)
        return tuple(buckets)


@dataclass(frozen=True)
class AllocationReceipt:
    request_id: str
    payload_hash: str
    result_json: str
    reservation: Reservation | None
    created_at: datetime
    expires_at: datetime

    @property
    def result(self) -> RecommendationResult:
        """Each access returns a freshly validated defensive copy."""
        return RecommendationResult.model_validate_json(self.result_json)


class AllocationStore(VirtualLoadReader, Protocol):
    @property
    def decision_lock(self) -> asyncio.Lock: ...

    async def lookup(self, request_id: str, payload_hash: str) -> AllocationReceipt | None: ...

    async def reserve(
        self,
        request_id: str,
        payload_hash: str,
        result: RecommendationResult,
        reservation: Reservation | None,
    ) -> AllocationReceipt: ...

    async def reset(self) -> None: ...


class Recommender(Protocol):
    async def recommend(self, request: RecommendationRequest) -> RecommendationResult: ...


class AllocationCoordinator:
    """One-worker correctness-first serialized read/decide/commit lifecycle.

    The factory binds C5's read-only provider to this exact store. Multiple
    coordinators share the store's decision lock. TTL pruning may occur during
    routing; reservation remains atomic. Cancellation before commit writes
    nothing. No external await occurs after a successful commit.
    """

    def __init__(
        self,
        *,
        store: AllocationStore,
        service_factory: Callable[[VirtualLoadReader], Recommender],
        charge_duration_minutes: float,
        expected_load: float = 1.0,
    ) -> None:
        self._duration = _reservation_duration(charge_duration_minutes)
        self._load = _number(expected_load, "expected_load")
        self._store = store
        self._service = service_factory(store)

    async def recommend(self, request: RecommendationRequest) -> RecommendationResult:
        validated = _validated_request(request)
        payload_hash = canonical_payload_hash(validated)
        async with self._store.decision_lock:
            existing = await self._store.lookup(validated.request_id, payload_hash)
            if existing is not None:
                return existing.result
            result = await self._service.recommend(validated.model_copy(deep=True))
            reservation = None
            if result.primary is not None:
                reservation = Reservation(
                    scenario=validated.scenario,
                    station_id=result.primary.station_id,
                    eta=result.primary.eta,
                    charge_duration_minutes=self._duration,
                    expected_load=self._load,
                )
            receipt = await self._store.reserve(
                validated.request_id,
                payload_hash,
                result,
                reservation,
            )
            return receipt.result

    async def reset(self) -> None:
        await self._store.reset()


@dataclass(frozen=True)
class CandidateMetadata:
    travel_minutes: float
    working_ports: int

    def __post_init__(self) -> None:
        _number(self.travel_minutes, "travel_minutes")
        if isinstance(self.working_ports, bool) or not isinstance(self.working_ports, int):
            raise ValueError("working_ports must be a positive integer")
        _number(self.working_ports, "working_ports", positive=True)


CandidateKey = tuple[Scenario, str, datetime]


class RecommendationAllocationStrategy:
    """Pure simulation adapter; never guesses duration, capacity or backup routes."""

    def __init__(
        self,
        *,
        ranking_config: RankingConfig,
        metadata: Mapping[CandidateKey, CandidateMetadata],
        virtual_loads: Mapping[CandidateKey, float],
    ) -> None:
        self._ranking = ranking_config
        self._metadata = MappingProxyType(dict(metadata))
        self._loads = MappingProxyType(
            {key: _number(value, "virtual_load") for key, value in virtual_loads.items()}
        )
        for key, measurement in self._metadata.items():
            Scenario(key[0])
            bucket_start(key[2], aligned=True)
            if not isinstance(measurement, CandidateMetadata):
                raise ValueError("metadata must contain CandidateMetadata measurements")
            CandidateMetadata(measurement.travel_minutes, measurement.working_ports)

    def select(self, context: AllocationContext) -> RankedPlan:
        payload = context.model_dump(mode="json")
        _canonical_json(payload)
        validated = AllocationContext.model_validate(payload)
        inputs = []
        loads = {}
        seen = set()
        for candidate in validated.candidates:
            if candidate.arrival_soc_pct < self._ranking.min_arrival_soc_pct:
                continue
            if candidate.station_id in seen:
                raise ValueError("duplicate station candidate")
            seen.add(candidate.station_id)
            key = (validated.request.scenario, candidate.station_id, candidate.eta)
            bucket_start(candidate.eta, aligned=True)
            measurement = self._metadata.get(key)
            if measurement is None:
                raise ValueError(f"missing verified metadata for {key}")
            inputs.append(
                RankingInput(candidate, measurement.travel_minutes, measurement.working_ports)
            )
            loads[candidate.station_id] = self._loads.get(key, 0.0)
        ranked = rank_candidates(inputs, self._ranking, loads)
        primary = ranked[0] if ranked else None
        if primary is None:
            return RankedPlan(
                primary=None,
                backup=None,
                plan_p=None,
                reasons=["No eligible charging station is available for allocation."],
            )
        return RankedPlan(
            primary=primary,
            backup=None,
            plan_p=primary.p_available,
            reasons=["Primary selected; no independently verified fallback reachability evidence."],
        )

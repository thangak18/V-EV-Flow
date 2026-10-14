from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import RequestConflictError
from app.backend.infrastructure.state import virtual_load as store_module
from app.backend.modules.recommendation import allocation
from app.backend.modules.recommendation.tests.test_service import OBSERVED


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2030, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def result(request_id: str = "req-c5", *, primary: bool = True):
    from app.backend.contracts.enums import DataType
    from app.backend.contracts.recommendation import Plan, RecommendationResult

    plan = Plan(
        station_id="S1",
        eta=OBSERVED,
        distance_km=10,
        detour_km=0,
        arrival_soc_pct=60,
        p_available=0.9,
    )
    return RecommendationResult(
        request_id=request_id,
        primary=plan if primary else None,
        backup=None,
        plan_p=0.9 if primary else None,
        reasons=["original"],
        model_version="test",
        allocation_method="test",
        data_type=DataType.MOCK,
    )


def reservation(**changes: Any):
    values: dict[str, Any] = dict(
        scenario=Scenario.NORMAL,
        station_id="S1",
        eta=OBSERVED,
        charge_duration_minutes=20,
        expected_load=1,
    )
    values.update(changes)
    return allocation.Reservation(**values)


@pytest.mark.parametrize("duration,count", [(20, 4), (12, 3), (0.1, 1), (5, 1)])
async def test_half_open_buckets_and_flooring(duration: float, count: int) -> None:
    store = store_module.VirtualLoadStore()
    await store.reserve("req-c5", "hash", result(), reservation(charge_duration_minutes=duration))
    for index in range(count):
        assert await store.snapshot(
            OBSERVED + timedelta(minutes=index * 5 + 2), Scenario.NORMAL
        ) == {"S1": 1.0}
    assert await store.snapshot(OBSERVED + timedelta(minutes=count * 5), Scenario.NORMAL) == {}
    assert await store.snapshot(OBSERVED - timedelta(seconds=1), Scenario.NORMAL) == {}
    assert await store.snapshot(OBSERVED, Scenario.TET) == {}


def test_reservation_duration_has_a_bounded_bucket_count() -> None:
    maximum = allocation.MAX_RESERVATION_DURATION_MINUTES
    allowed = reservation(charge_duration_minutes=maximum)
    assert len(allowed.buckets()) == allocation.MAX_RESERVATION_BUCKETS
    with pytest.raises(ValueError, match="at most"):
        reservation(charge_duration_minutes=maximum + 0.1)
    with pytest.raises(ValueError, match="at most"):
        reservation(charge_duration_minutes=50_000)


async def test_rejected_oversized_reservation_cannot_change_store_state() -> None:
    store = store_module.VirtualLoadStore()
    with pytest.raises(ValueError, match="at most"):
        reservation(charge_duration_minutes=50_000)
    assert await store.lookup("req-c5", "hash") is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    await store.reserve("req-c5", "hash", result(), reservation())
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1}


async def test_replay_defensive_copies_and_global_conflicts() -> None:
    store = store_module.VirtualLoadStore()
    original = result()
    receipt = await store.reserve("req-c5", "hash", original, reservation())
    original.reasons.append("mutated")
    receipt.result.reasons.append("mutated again")
    replay = await store.reserve("req-c5", "hash", result(primary=False), None)
    assert replay.result.reasons == ["original"]
    assert replay.result.primary is not None
    snapshot = await store.snapshot(OBSERVED, Scenario.NORMAL)
    with pytest.raises(TypeError):
        cast(MutableMapping[str, float], snapshot)["S1"] = 99
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1.0}
    with pytest.raises(RequestConflictError):
        await store.reserve("req-c5", "other", result(), reservation(scenario=Scenario.TET))
    with pytest.raises(RequestConflictError):
        await store.lookup("req-c5", "other")


async def test_no_plan_replay_and_reset() -> None:
    store = store_module.VirtualLoadStore()
    await store.reserve("req-c5", "hash", result(primary=False), None)
    assert (await store.reserve("req-c5", "hash", result(), reservation())).result.primary is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    await store.reset()
    assert await store.lookup("req-c5", "other") is None
    await store.reserve("req-c5", "other", result(), reservation())
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1.0}


async def test_ttl_processing_clock_exact_boundary_and_fractional_reversal() -> None:
    clock = Clock()
    store = store_module.VirtualLoadStore(ttl=timedelta(minutes=10), clock=clock)
    await store.reserve("first", "hash", result("first"), reservation(expected_load=0.1))
    clock.now += timedelta(minutes=5)
    await store.reserve("second", "hash", result("second"), reservation(expected_load=0.2))
    clock.now += timedelta(minutes=5)
    assert await store.lookup("first", "hash") is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 0.2}
    assert await store.lookup("second", "hash") is not None
    clock.now += timedelta(minutes=5)
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    await store.reserve("first", "different", result("first"), reservation())


@pytest.mark.parametrize("same_id", [True, False])
async def test_fifty_concurrent_reserves(same_id: bool) -> None:
    store = store_module.VirtualLoadStore()
    identifiers = ["same" if same_id else f"req-{index}" for index in range(50)]
    await asyncio.wait_for(
        asyncio.gather(
            *(
                store.reserve(identifier, "hash", result(identifier), reservation())
                for identifier in identifiers
            )
        ),
        timeout=5,
    )
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1 if same_id else 50}


async def test_conflicting_concurrent_reserves_commit_only_one() -> None:
    store = store_module.VirtualLoadStore()
    outcomes = await asyncio.gather(
        store.reserve("req-c5", "a", result(), reservation()),
        store.reserve("req-c5", "b", result(), reservation()),
        return_exceptions=True,
    )
    assert sum(isinstance(item, RequestConflictError) for item in outcomes) == 1
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1}


@pytest.mark.parametrize(
    "changes",
    [
        {"station_id": ""},
        {"station_id": " "},
        {"scenario": "invalid"},
        {"eta": OBSERVED.replace(tzinfo=None)},
        {"eta": OBSERVED.astimezone(UTC)},
        {"eta": OBSERVED + timedelta(seconds=1)},
        {"eta": OBSERVED + timedelta(minutes=1)},
        {"charge_duration_minutes": 0},
        {"charge_duration_minutes": -1},
        {"charge_duration_minutes": float("inf")},
        {"charge_duration_minutes": True},
        {"charge_duration_minutes": 10**400},
        {"charge_duration_minutes": 1e30},
        {"expected_load": -1},
        {"expected_load": float("nan")},
        {"expected_load": True},
    ],
)
def test_invalid_reservation(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        reservation(**changes)


@pytest.mark.parametrize("ttl", [timedelta(0), timedelta(seconds=-1)])
def test_invalid_ttl(ttl: timedelta) -> None:
    with pytest.raises(ValueError):
        store_module.VirtualLoadStore(ttl=ttl)


async def test_invalid_snapshot_and_atomic_result_validation() -> None:
    store = store_module.VirtualLoadStore()
    with pytest.raises(ValueError):
        await store.snapshot(OBSERVED.replace(tzinfo=None), Scenario.NORMAL)
    invalid = result()
    invalid.request_id = "another"
    with pytest.raises(ValueError):
        await store.reserve("req-c5", "hash", invalid, reservation())
    assert await store.lookup("req-c5", "hash") is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}


async def test_station_isolation_zero_load_and_expiry_while_reserving() -> None:
    clock = Clock()
    store = store_module.VirtualLoadStore(ttl=timedelta(minutes=10), clock=clock)
    await store.reserve("zero", "hash", result("zero"), reservation(expected_load=0))
    assert await store.lookup("zero", "hash") is not None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    await store.reserve("first", "hash", result("first"), reservation())
    second = result("second")
    assert second.primary is not None
    second.primary.station_id = "S2"
    await store.reserve("second", "hash", second, reservation(station_id="S2"))
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1, "S2": 1}
    clock.now += timedelta(minutes=10)
    await asyncio.wait_for(
        asyncio.gather(
            *(
                store.reserve(f"new-{index}", "hash", result(f"new-{index}"), reservation())
                for index in range(50)
            ),
            store.snapshot(OBSERVED, Scenario.NORMAL),
        ),
        timeout=3,
    )
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 50}
    assert await store.lookup("second", "hash") is None


async def test_load_overflow_rejects_without_partial_buckets_or_receipt() -> None:
    store = store_module.VirtualLoadStore()
    await store.reserve("first", "hash", result("first"), reservation(expected_load=1e308))
    with pytest.raises(ValueError, match="overflow"):
        await store.reserve("second", "hash", result("second"), reservation(expected_load=1e308))
    assert await store.lookup("second", "hash") is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1e308}


@pytest.mark.parametrize("primary,reserved", [(True, False), (False, True)])
async def test_primary_and_reservation_must_correspond(primary: bool, reserved: bool) -> None:
    store = store_module.VirtualLoadStore()
    with pytest.raises(ValueError, match="primary"):
        await store.reserve(
            "req-c5", "hash", result(primary=primary), reservation() if reserved else None
        )
    assert await store.lookup("req-c5", "hash") is None


async def test_mismatched_station_and_mutated_result_reject_without_commit() -> None:
    store = store_module.VirtualLoadStore()
    with pytest.raises(ValueError, match="selected primary"):
        await store.reserve("req-c5", "hash", result(), reservation(station_id="S2"))
    invalid = result()
    assert invalid.primary is not None
    invalid.primary.distance_km = -1
    with pytest.raises(ValueError):
        await store.reserve("req-c5", "hash", invalid, reservation())
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    assert await store.lookup("req-c5", "hash") is None


async def test_invalid_clock_and_expiry_overflow_do_not_commit() -> None:
    clock = Clock()
    store = store_module.VirtualLoadStore(clock=clock)
    clock.now = clock.now.replace(tzinfo=None)
    with pytest.raises(ValueError, match="clock"):
        await store.reserve("req-c5", "hash", result(), reservation())
    clock.now = datetime.max.replace(tzinfo=UTC)
    with pytest.raises(ValueError, match="expiry"):
        await store.reserve("req-c5", "hash", result(), reservation())
    clock.now = datetime(2030, 1, 1, tzinfo=UTC)
    assert await store.lookup("req-c5", "hash") is None


@pytest.mark.parametrize("identifier,payload_hash", [("", "hash"), ("req-c5", "")])
async def test_nonempty_receipt_identity(identifier: str, payload_hash: str) -> None:
    store = store_module.VirtualLoadStore()
    with pytest.raises(ValueError):
        await store.reserve(identifier, payload_hash, result(), reservation())


def test_tiny_positive_duration_must_advance_datetime() -> None:
    with pytest.raises(ValueError, match="advance ETA"):
        reservation(charge_duration_minutes=1e-30)


@pytest.mark.parametrize("leg", ["primary", "backup"])
@pytest.mark.parametrize("measurement", ["distance_km", "detour_km"])
@pytest.mark.parametrize("value", ["Infinity", "1e309"])
async def test_coerced_nonfinite_result_rejects_atomically(
    leg: str,
    measurement: str,
    value: str,
) -> None:
    store = store_module.VirtualLoadStore()
    output = result()
    assert output.primary is not None
    output.backup = output.primary.model_copy(deep=True)
    setattr(getattr(output, leg), measurement, value)
    with pytest.raises(ValueError):
        await store.reserve("req-c5", "hash", output, reservation())
    assert await store.lookup("req-c5", "hash") is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}

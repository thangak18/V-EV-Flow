import asyncio
from datetime import timedelta

import pytest

from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import RequestConflictError
from app.backend.infrastructure.state.sqlite import SQLiteVirtualLoadStore
from app.backend.modules.recommendation.allocation import Reservation
from app.backend.tests.infrastructure.test_virtual_load import OBSERVED as ETA
from app.backend.tests.infrastructure.test_virtual_load import result


@pytest.mark.asyncio
async def test_durable_receipts_conflict_and_reset(tmp_path) -> None:
    path = tmp_path / "load.sqlite3"
    first = SQLiteVirtualLoadStore(path)
    reservation = Reservation(Scenario.NORMAL, "S1", ETA, 60)
    receipt = await first.reserve("r", "hash", result("r"), reservation)
    second = SQLiteVirtualLoadStore(path)
    found = await second.lookup("r", "hash")
    assert found is not None and found.result == receipt.result
    assert (await second.snapshot(ETA, Scenario.NORMAL))["S1"] == 1
    with pytest.raises(RequestConflictError):
        await second.lookup("r", "different")
    await second.reset()
    assert await first.lookup("r", "hash") is None
    assert not await first.snapshot(ETA, Scenario.NORMAL)


@pytest.mark.asyncio
async def test_two_independent_store_decisions_serialize_and_cancel_rolls_back(tmp_path) -> None:
    path = tmp_path / "load.sqlite3"
    first, second = SQLiteVirtualLoadStore(path), SQLiteVirtualLoadStore(path)
    order = []

    async def decide(store, request_id):
        async with store.decision_lock:
            order.append(request_id + "-start")
            await asyncio.sleep(0.04)
            await store.reserve(
                request_id,
                "hash",
                result(request_id),
                Reservation(Scenario.NORMAL, "S1", ETA, 60),
            )
            order.append(request_id + "-end")

    await asyncio.gather(decide(first, "a"), decide(second, "b"))
    assert order in (
        ["a-start", "a-end", "b-start", "b-end"],
        ["b-start", "b-end", "a-start", "a-end"],
    )
    assert (await first.snapshot(ETA, Scenario.NORMAL))["S1"] == 2
    with pytest.raises(asyncio.CancelledError):
        async with first.decision_lock:
            await first.reserve(
                "c", "hash", result("c"), Reservation(Scenario.NORMAL, "S1", ETA, 60)
            )
            raise asyncio.CancelledError
    assert await second.lookup("c", "hash") is None


@pytest.mark.asyncio
async def test_ttl_survives_reopen_and_prunes_own_load(tmp_path) -> None:
    clock = [ETA]
    path = tmp_path / "ttl.sqlite3"
    first = SQLiteVirtualLoadStore(path, ttl=timedelta(seconds=10), clock=lambda: clock[0])
    await first.reserve("r", "h", result("r"), Reservation(Scenario.NORMAL, "S1", ETA, 60))
    clock[0] += timedelta(seconds=10)
    reopened = SQLiteVirtualLoadStore(path, clock=lambda: clock[0])
    assert await reopened.lookup("r", "h") is None
    assert not await reopened.snapshot(ETA, Scenario.NORMAL)

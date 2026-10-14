from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import timedelta
from typing import Any

import pytest

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import RequestConflictError
from app.backend.contracts.ports import AllocationStrategy
from app.backend.contracts.recommendation import AllocationContext, FeasibleCandidate
from app.backend.infrastructure.state import virtual_load as store_module
from app.backend.modules.recommendation import allocation
from app.backend.modules.recommendation.ranking import RankingConfig
from app.backend.modules.recommendation.service import RecommendationService, VirtualLoadReader
from app.backend.modules.recommendation.tests.test_service import (
    OBSERVED,
    FakePredictor,
    FakeRoutes,
    FakeStations,
    FakeStatuses,
    request,
    route,
    station,
)
from app.backend.tests.infrastructure.test_virtual_load import Clock, result


def test_hash_canonical_and_no_mutation() -> None:
    payload = request()
    original = payload.model_dump(mode="json")
    expected = hashlib.sha256(
        json.dumps(
            original,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    assert allocation.canonical_payload_hash(payload) == expected
    assert (
        allocation.canonical_payload_hash(
            type(payload).model_validate(dict(reversed(list(original.items()))))
        )
        == expected
    )
    assert payload.model_dump(mode="json") == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("soc", 70),
        ("origin", 10.1),
        ("destination", 10.6),
        ("depart_time", OBSERVED + timedelta(minutes=5)),
        ("scenario", Scenario.TET),
    ],
)
def test_hash_covers_full_payload(field: str, value: Any) -> None:
    original = request()
    changed = original.model_copy(deep=True)
    if field == "soc":
        changed.vehicle.soc_pct = value
    elif field in ("origin", "destination"):
        getattr(changed, field).lat = value
    else:
        setattr(changed, field, value)
    assert allocation.canonical_payload_hash(original) != allocation.canonical_payload_hash(changed)


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_hash_revalidates_mutated_request(value: float) -> None:
    payload = request()
    payload.vehicle.battery_kwh = value
    with pytest.raises(ValueError):
        allocation.canonical_payload_hash(payload)


class FixedService:
    def __init__(self) -> None:
        self.calls = 0
        self.started = asyncio.Event()
        self.proceed = asyncio.Event()
        self.proceed.set()

    async def recommend(self, payload):
        self.calls += 1
        self.started.set()
        await self.proceed.wait()
        return result(payload.request_id)


def coordinator(store, service):
    return allocation.AllocationCoordinator(
        store=store,
        service_factory=lambda reader: service,
        charge_duration_minutes=12,
        expected_load=1,
    )


async def test_duplicate_coordinators_share_decision_lock_and_replay() -> None:
    store = store_module.VirtualLoadStore()
    service = FixedService()
    service.proceed.clear()
    first, second = coordinator(store, service), coordinator(store, service)
    pending = asyncio.gather(
        *((first if index % 2 else second).recommend(request()) for index in range(50))
    )
    await asyncio.wait_for(service.started.wait(), timeout=2)
    try:
        assert service.calls == 1
    finally:
        service.proceed.set()
        outputs = await asyncio.wait_for(pending, timeout=5)
    assert service.calls == 1
    assert all(item.model_dump() == outputs[0].model_dump() for item in outputs)
    outputs[0].reasons.append("mutated")
    assert (await first.recommend(request())).reasons == ["original"]
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {"S1": 1}
    conflicting = request()
    conflicting.scenario = Scenario.TET
    with pytest.raises(RequestConflictError):
        await first.recommend(conflicting)


async def test_cancellation_releases_lock_without_reservation() -> None:
    store = store_module.VirtualLoadStore()
    service = FixedService()
    service.proceed.clear()
    allocator = coordinator(store, service)
    pending = asyncio.create_task(allocator.recommend(request()))
    await service.started.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert await store.lookup("req-c5", allocation.canonical_payload_hash(request())) is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    service.proceed.set()
    await asyncio.wait_for(allocator.recommend(request()), timeout=2)


async def test_independent_store_reset_waits_for_active_decision() -> None:
    store = store_module.VirtualLoadStore()
    service = FixedService()
    service.proceed.clear()
    allocator = coordinator(store, service)
    pending = asyncio.create_task(allocator.recommend(request()))
    await service.started.wait()
    reset_started = asyncio.Event()

    async def reset():
        reset_started.set()
        await store.reset()

    resetting = asyncio.create_task(reset())
    await reset_started.wait()
    assert not resetting.done()
    service.proceed.set()
    await asyncio.wait_for(asyncio.gather(pending, resetting), timeout=2)
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    assert await store.lookup("req-c5", allocation.canonical_payload_hash(request())) is None
    await allocator.recommend(request())
    await allocator.reset()
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}


def candidate(station_id: str, probability: float, soc: float = 60):
    return FeasibleCandidate(
        station_id=station_id,
        distance_km=10,
        detour_km=0,
        arrival_soc_pct=soc,
        p_available=probability,
        eta=OBSERVED,
    )


def test_pure_strategy_metadata_load_and_no_unverified_backup() -> None:
    payload = request()
    context = AllocationContext(
        request=payload, candidates=(candidate("S1", 0.9), candidate("S2", 0.85))
    )
    metadata = {
        (Scenario.NORMAL, station_id, OBSERVED): allocation.CandidateMetadata(10, 2)
        for station_id in ("S1", "S2")
    }
    loads = {(Scenario.NORMAL, "S1", OBSERVED): 10.0}
    strategy = allocation.RecommendationAllocationStrategy(
        ranking_config=RankingConfig(weight_travel=0, weight_soc_risk=0, weight_virtual_load=1),
        metadata=metadata,
        virtual_loads=loads,
    )
    assert isinstance(strategy, AllocationStrategy)
    before = context.model_dump()
    plan = strategy.select(context)
    assert plan.primary is not None and plan.primary.station_id == "S2"
    assert plan.primary.p_available == 0.85 and plan.plan_p == 0.85
    assert plan.backup is None
    assert any("fallback" in reason.lower() for reason in plan.reasons)
    assert context.model_dump() == before
    loads.clear()
    metadata.clear()
    assert strategy.select(context).model_dump() == plan.model_dump()


def test_strategy_rejects_missing_metadata_and_filters_soc() -> None:
    context = AllocationContext(request=request(), candidates=(candidate("S1", 0.9),))
    strategy = allocation.RecommendationAllocationStrategy(
        ranking_config=RankingConfig(),
        metadata={},
        virtual_loads={},
    )
    with pytest.raises(ValueError, match="metadata"):
        strategy.select(context)
    context.candidates[0].arrival_soc_pct = 5
    plan = strategy.select(context)
    assert plan.primary is None and plan.backup is None and plan.plan_p is None
    assert plan.reasons == ["No eligible charging station is available for allocation."]


def test_strategy_primary_only_reason_requires_a_primary() -> None:
    key = (Scenario.NORMAL, "S1", OBSERVED)
    strategy = allocation.RecommendationAllocationStrategy(
        ranking_config=RankingConfig(),
        metadata={key: allocation.CandidateMetadata(10, 2)},
        virtual_loads={},
    )
    selected = strategy.select(
        AllocationContext(request=request(), candidates=(candidate("S1", 0.9),))
    )
    assert selected.primary is not None
    assert selected.backup is None
    assert selected.plan_p == selected.primary.p_available
    assert selected.reasons == [
        "Primary selected; no independently verified fallback reachability evidence."
    ]


class GatedRoutes(FakeRoutes):
    def __init__(self, routes) -> None:
        super().__init__(routes)
        self.started = asyncio.Event()
        self.proceed = asyncio.Event()
        self.entered = 0

    async def get_routes(self, request):
        self.entered += 1
        self.started.set()
        await self.proceed.wait()
        return await super().get_routes(request)


def live_coordinator(store, *, gated: bool = False):
    s1, s2 = station("S1"), station("S2")
    origin, destination = (10.0, 106.0), (10.5, 106.5)
    p1, p2 = (s1.lat, s1.lng), (s2.lat, s2.lng)
    route_factory = GatedRoutes if gated else FakeRoutes
    routes = route_factory(
        {
            (origin, destination): (route(40, 35),),
            (origin, p1): (route(10, 10),),
            (origin, p2): (route(10, 10),),
            (p1, destination): (route(20, 20),),
            (p2, destination): (route(20, 20),),
            (p1, p2): (route(5, 10),),
            (p2, p1): (route(5, 10),),
        }
    )
    repository = FakeStations((s1, s2))
    predictor = FakePredictor({"S1": 0.9, "S2": 0.85})

    def factory(reader: VirtualLoadReader) -> RecommendationService:
        return RecommendationService(
            station_repository=repository,
            status_repositories={
                scenario: FakeStatuses(repository, scenario=scenario) for scenario in Scenario
            },
            route_provider=routes,
            predictors=dict.fromkeys(Scenario, predictor),
            ranking_config=RankingConfig(
                weight_travel=0,
                weight_soc_risk=0,
                weight_virtual_load=1,
            ),
            max_prediction_horizon_minutes=dict.fromkeys(Scenario, 120),
            data_type=DataType.MOCK,
            virtual_load_provider=reader,
        )

    return (
        allocation.AllocationCoordinator(
            store=store,
            service_factory=factory,
            charge_duration_minutes=5,
        ),
        predictor,
        routes,
    )


async def test_real_c5_concurrent_decisions_switch_stations_and_preserve_probability() -> None:
    store = store_module.VirtualLoadStore()
    allocator, predictor, routes = live_coordinator(store, gated=True)
    assert isinstance(routes, GatedRoutes)
    first_request, second_request = request(), request()
    second_request.request_id = "driver-2"
    first_pending = asyncio.create_task(allocator.recommend(first_request))
    await asyncio.wait_for(routes.started.wait(), timeout=2)
    second_started = asyncio.Event()

    async def second_driver():
        second_started.set()
        return await allocator.recommend(second_request)

    second_pending = asyncio.create_task(second_driver())
    await asyncio.wait_for(second_started.wait(), timeout=2)
    try:
        assert routes.entered == 1
    finally:
        routes.proceed.set()
        first, second = await asyncio.wait_for(
            asyncio.gather(first_pending, second_pending), timeout=3
        )
    assert first.primary is not None and first.primary.station_id == "S1"
    assert second.primary is not None and second.primary.station_id == "S2"
    assert first.primary.p_available == 0.9 and second.primary.p_available == 0.85
    assert await store.snapshot(OBSERVED + timedelta(minutes=10), Scenario.NORMAL) == {
        "S1": 1,
        "S2": 1,
    }
    assert await store.snapshot(OBSERVED + timedelta(minutes=20), Scenario.NORMAL) == {}
    call_count = (len(predictor.requests), len(routes.requests))
    assert (await allocator.recommend(first_request)).model_dump() == first.model_dump()
    assert (len(predictor.requests), len(routes.requests)) == call_count


@pytest.mark.parametrize("separate", ["scenario", "eta"])
async def test_real_c5_isolates_scenario_and_arrival_buckets(separate: str) -> None:
    store = store_module.VirtualLoadStore()
    allocator, _, _ = live_coordinator(store)
    first = await allocator.recommend(request())
    other = request()
    other.request_id = "other"
    if separate == "scenario":
        other.scenario = Scenario.TET
    else:
        other.depart_time += timedelta(minutes=5)
    second = await allocator.recommend(other)
    assert first.primary is not None and first.primary.station_id == "S1"
    assert second.primary is not None and second.primary.station_id == "S1"


async def test_fifty_unique_coordinated_c5_requests_preserve_all_increments() -> None:
    store = store_module.VirtualLoadStore()
    allocator, _, _ = live_coordinator(store)
    requests = [
        request().model_copy(update={"request_id": f"driver-{index}"}) for index in range(50)
    ]
    outputs = await asyncio.wait_for(
        asyncio.gather(*(allocator.recommend(payload) for payload in requests)), timeout=5
    )
    assert all(output.primary is not None for output in outputs)
    counts = await store.snapshot(OBSERVED + timedelta(minutes=10), Scenario.NORMAL)
    assert sum(counts.values()) == 50
    assert set(counts) == {"S1", "S2"}


async def test_coordinator_no_plan_receipt_and_failure_does_not_commit() -> None:
    store = store_module.VirtualLoadStore()

    class NoPlan:
        calls = 0

        async def recommend(self, payload):
            self.calls += 1
            return result(payload.request_id, primary=False)

    service = NoPlan()
    allocator = coordinator(store, service)
    assert (await allocator.recommend(request())).primary is None
    assert (await allocator.recommend(request())).primary is None
    assert service.calls == 1
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    await store.reset()

    class Failing:
        async def recommend(self, payload):
            raise RuntimeError("upstream outage")

    with pytest.raises(RuntimeError, match="outage"):
        await coordinator(store, Failing()).recommend(request())
    assert await store.lookup("req-c5", allocation.canonical_payload_hash(request())) is None


@pytest.mark.parametrize(
    "travel,ports", [(-1, 2), (True, 2), (float("inf"), 2), (10, 0), (10, True), (10, 2.5)]
)
def test_strategy_invalid_metadata(travel: Any, ports: Any) -> None:
    with pytest.raises(ValueError):
        allocation.CandidateMetadata(travel, ports)


def test_strategy_empty_ties_and_actual_travel_measurements() -> None:
    metadata = {
        (Scenario.NORMAL, station_id, OBSERVED): allocation.CandidateMetadata(10, 2)
        for station_id in ("S1", "S2")
    }
    context = AllocationContext(
        request=request(), candidates=(candidate("S2", 0.9), candidate("S1", 0.9))
    )
    strategy = allocation.RecommendationAllocationStrategy(
        ranking_config=RankingConfig(),
        metadata=metadata,
        virtual_loads={},
    )
    first = strategy.select(context).primary
    assert first is not None and first.station_id == "S1"
    metadata[(Scenario.NORMAL, "S1", OBSERVED)] = allocation.CandidateMetadata(100, 2)
    penalized = allocation.RecommendationAllocationStrategy(
        ranking_config=RankingConfig(),
        metadata=metadata,
        virtual_loads={},
    )
    second = penalized.select(context).primary
    assert second is not None and second.station_id == "S2"
    context.candidates = ()
    assert strategy.select(context).primary is None


def test_strategy_duplicate_candidates_and_invalid_metadata_object() -> None:
    key = (Scenario.NORMAL, "S1", OBSERVED)
    invalid_metadata: Any = {key: None}
    with pytest.raises(ValueError, match="CandidateMetadata"):
        allocation.RecommendationAllocationStrategy(
            ranking_config=RankingConfig(),
            metadata=invalid_metadata,
            virtual_loads={},
        )
    strategy = allocation.RecommendationAllocationStrategy(
        ranking_config=RankingConfig(),
        metadata={key: allocation.CandidateMetadata(10, 2)},
        virtual_loads={},
    )
    with pytest.raises(ValueError, match="duplicate"):
        strategy.select(
            AllocationContext(
                request=request(),
                candidates=(candidate("S1", 0.9), candidate("S1", 0.8)),
            )
        )


async def test_coordinator_ttl_pruning_overlaps_awaited_recommendation() -> None:
    clock = Clock()
    store = store_module.VirtualLoadStore(ttl=timedelta(minutes=10), clock=clock)
    allocator, _, routes = live_coordinator(store, gated=True)
    assert isinstance(routes, GatedRoutes)
    routes.proceed.set()
    await allocator.recommend(request())
    routes.proceed.clear()
    routes.started.clear()
    other = request()
    other.request_id = "after-expiry"
    pending = asyncio.create_task(allocator.recommend(other))
    await asyncio.wait_for(routes.started.wait(), timeout=2)
    clock.now += timedelta(minutes=10)
    assert await store.snapshot(OBSERVED + timedelta(minutes=10), Scenario.NORMAL) == {}
    routes.proceed.set()
    output = await asyncio.wait_for(pending, timeout=2)
    assert output.primary is not None and output.primary.station_id == "S1"
    assert await store.lookup("req-c5", allocation.canonical_payload_hash(request())) is None
    assert await store.snapshot(OBSERVED + timedelta(minutes=10), Scenario.NORMAL) == {"S1": 1}


async def test_coordinator_rejects_coerced_nonfinite_result_and_can_retry() -> None:
    store = store_module.VirtualLoadStore()

    class Nonfinite:
        async def recommend(self, payload):
            output = result(payload.request_id)
            assert output.primary is not None
            setattr(output.primary, "detour_km", "1e309")
            return output

    with pytest.raises(ValueError):
        await coordinator(store, Nonfinite()).recommend(request())
    assert await store.lookup("req-c5", allocation.canonical_payload_hash(request())) is None
    assert await store.snapshot(OBSERVED, Scenario.NORMAL) == {}
    output = await coordinator(store, FixedService()).recommend(request())
    assert output.primary is not None and output.primary.detour_km == 0

from datetime import datetime, timedelta, timezone

import pytest

from app.backend.contracts.enums import Scenario, Strategy
from app.backend.contracts.recommendation import (
    AllocationContext,
    RankedCandidate,
    RankedPlan,
    Vehicle,
)
from app.backend.contracts.simulation import (
    BackgroundArrival,
    FixtureBundle,
    ScenarioConfig,
    SimulationRequest,
)
from app.backend.contracts.stations import Station
from app.backend.modules.simulation.baselines import NearestStrategy
from app.backend.modules.simulation.metrics import (
    OutcomeStatus,
    VehicleOutcome,
    calculate_metrics,
)
from app.backend.modules.simulation.runner import DefaultSimulationRunner, compare_strategies

START = datetime(2026, 10, 12, 0, 0, tzinfo=timezone(timedelta(hours=7)))


def make_station(
    station_id: str, lat: float, lng: float, ports: int, power: float = 60.0
) -> Station:
    return Station(
        station_id=station_id, name=station_id, lat=lat, lng=lng, n_ports=ports, power_kw=power,
        connector_types=["CCS2"], network="test", station_type="urban", source="test",
        assumptions=["test"],
    )  # fmt: skip


STATIONS = (
    make_station("S001", 10.80, 106.70, 1),
    make_station("S002", 10.60, 106.90, 4),
    make_station("S003", 10.40, 107.05, 4),
)


def make_config(compliance: float = 1.0, seed: int = 5) -> ScenarioConfig:
    return ScenarioConfig(
        scenario=Scenario.NORMAL, seed=seed, start=START, end=START + timedelta(hours=48),
        step_minutes=5, demand_multiplier=1.0, compliance_rate=compliance,
    )  # fmt: skip


def make_vehicles(count: int, soc: float = 80.0) -> tuple[Vehicle, ...]:
    return tuple(
        Vehicle(soc_pct=soc, battery_kwh=60.0, consumption_kwh_per_km=0.16, connector_type="CCS2")
        for _ in range(count)
    )


def make_bundle(
    vehicles: tuple[Vehicle, ...], blocked: bool = False, seed: int = 5
) -> FixtureBundle:
    arrivals = (BackgroundArrival(station_id="S001", ts=START, vehicle_id="B1"),) if blocked else ()
    return FixtureBundle(
        vehicles=vehicles, background_arrivals=arrivals,
        service_durations=(100_000.0,) if blocked else (), port_events=(),
        scenario=Scenario.NORMAL, seed=seed,
    )  # fmt: skip


def make_runner(bundle: FixtureBundle, config: ScenarioConfig | None = None, **kwargs):  # noqa: ANN003, ANN201
    config = config or make_config(seed=bundle.seed)
    return DefaultSimulationRunner(
        lambda _request: bundle, STATIONS, {Scenario.NORMAL: config}, **kwargs
    )


def make_request(
    count: int, strategy: Strategy = Strategy.NEAREST, seed: int = 5
) -> SimulationRequest:
    return SimulationRequest(
        scenario=Scenario.NORMAL, seed=seed, vehicle_count=count, strategy=strategy
    )


def test_all_strategies_receive_same_fixture_hash() -> None:
    runner = make_runner(make_bundle(make_vehicles(20), blocked=True))
    results = compare_strategies(runner, make_request(20), runner.baseline_strategies())
    assert [item.strategy for item in results] == [Strategy.NEAREST, Strategy.CURRENTLY_AVAILABLE]
    assert len({item.fixture_hash for item in results}) == 1
    assert all(item.metrics.vehicle_count == 20 for item in results)


def test_failed_vehicles_remain_in_success_rate_denominator() -> None:
    outcomes = [
        VehicleOutcome("V1", OutcomeStatus.SUCCESS, detour_km=2.0, wait_minutes=0.0),
        VehicleOutcome("V2", OutcomeStatus.FAILED, wait_minutes=30.0),
    ]
    metrics = calculate_metrics(outcomes, vehicle_count=2)
    assert metrics.success_rate == 0.5
    assert metrics.failed_count == 1
    assert metrics.mean_detour_km == 2.0  # only vehicles with a station
    assert metrics.mean_wait_minutes == 15.0  # abandoned vehicles count their wait


def test_metric_edge_cases() -> None:
    assert calculate_metrics([], 0).success_rate == 0.0
    assert calculate_metrics([], 3).failed_count == 3  # vehicles without an outcome failed
    served = [VehicleOutcome("V1", OutcomeStatus.SERVED_AFTER_WAIT, wait_minutes=10.0)]
    assert calculate_metrics(served, 1).success_rate == 0.0  # not a success at arrival
    with pytest.raises(ValueError):
        calculate_metrics(served * 2, 1)


def test_currently_available_beats_nearest_when_nearest_station_is_blocked() -> None:
    runner = make_runner(make_bundle(make_vehicles(30), blocked=True))
    nearest, current = compare_strategies(runner, make_request(30), runner.baseline_strategies())
    assert current.metrics.success_rate > nearest.metrics.success_rate
    assert nearest.metrics.failed_count > current.metrics.failed_count
    assert nearest.metrics.mean_wait_minutes > current.metrics.mean_wait_minutes


def test_runs_are_reproducible_and_do_not_share_state() -> None:
    runner = make_runner(make_bundle(make_vehicles(25), blocked=True))
    first = compare_strategies(runner, make_request(25), runner.baseline_strategies())
    second = compare_strategies(runner, make_request(25), runner.baseline_strategies())
    assert first == second
    solo = runner.run(
        make_request(25, Strategy.CURRENTLY_AVAILABLE),
        runner.baseline_strategies()[Strategy.CURRENTLY_AVAILABLE],
    )
    assert solo == first[1]


class RecordingStrategy:
    model_version = "fake-v1"

    def __init__(self, choice: str | None = None) -> None:
        self.calls: list[AllocationContext] = []
        self._choice = choice

    def select(self, context: AllocationContext) -> RankedPlan:
        self.calls.append(context)
        ordered = sorted(context.candidates, key=lambda item: item.station_id)
        station_id = self._choice or ordered[0].station_id
        base = next((item for item in ordered if item.station_id == station_id), ordered[0])
        primary = RankedCandidate(
            **{**base.model_dump(), "station_id": station_id}, rank=1, score=1.0
        )
        return RankedPlan(primary=primary, backup=None, plan_p=None, reasons=["fake"])


def test_injected_ai_strategy_is_called_for_every_evaluated_vehicle() -> None:
    fake = RecordingStrategy()
    runner = make_runner(make_bundle(make_vehicles(12)))
    result = runner.run(make_request(12, Strategy.AI_ALLOCATION), fake)
    assert len(fake.calls) == 12
    assert result.strategy is Strategy.AI_ALLOCATION
    assert result.model_version == "fake-v1"
    assert all(len(call.candidates) == 3 for call in fake.calls)


def test_non_compliant_drivers_ignore_the_strategy() -> None:
    fake = RecordingStrategy()
    runner = make_runner(make_bundle(make_vehicles(12)), make_config(compliance=0.0))
    runner.run(make_request(12, Strategy.AI_ALLOCATION), fake)
    assert fake.calls == []


def test_vehicles_that_cannot_reach_any_station_fail_and_stay_counted() -> None:
    runner = make_runner(make_bundle(make_vehicles(8, soc=10.0)))
    result = runner.run(make_request(8), NearestStrategy())
    assert result.metrics.failed_count == 8
    assert result.metrics.success_rate == 0.0
    assert result.metrics.vehicle_count == 8


def test_strategy_choosing_a_non_candidate_station_fails_the_vehicle() -> None:
    runner = make_runner(make_bundle(make_vehicles(5)))

    # Plan names a real candidate id, but a strategy returning an unknown id must not crash.
    class Rogue:
        def select(self, context: AllocationContext) -> RankedPlan:
            base = context.candidates[0]
            ghost = RankedCandidate(**{**base.model_dump(), "station_id": "S999"}, rank=1, score=0)
            return RankedPlan(primary=ghost, backup=None, plan_p=None, reasons=[])

    result = runner.run(make_request(5), Rogue())
    assert result.metrics.failed_count == 5


def test_request_must_match_bundle_and_vehicle_count_must_fit() -> None:
    runner = make_runner(make_bundle(make_vehicles(3)))
    with pytest.raises(ValueError, match="scenario and seed"):
        runner.run(make_request(3, seed=99), NearestStrategy())
    with pytest.raises(ValueError, match="requested"):
        runner.run(make_request(4), NearestStrategy())


def test_free_ports_is_only_available_during_a_run() -> None:
    runner = make_runner(make_bundle(make_vehicles(1)))
    with pytest.raises(RuntimeError):
        runner.free_ports("S001")


def test_runtime_horizon_excludes_candidates_before_model_without_clipping() -> None:
    from app.backend.contracts.common import Coordinate
    from app.backend.modules.simulation.engine import SimulationEngine
    from app.backend.modules.simulation.trips import VehicleTrip

    calls = []
    config = make_config()
    runner = DefaultSimulationRunner(
        lambda request: make_bundle(make_vehicles(1)),
        STATIONS,
        {Scenario.NORMAL: config},
        availability=lambda station, now, eta: calls.append((now, eta)) or 0.5,
        max_prediction_horizon_minutes=5,
    )
    engine = SimulationEngine(STATIONS, Scenario.NORMAL)
    engine.step(START)
    trip = VehicleTrip(
        "v",
        make_vehicles(1)[0],
        Coordinate(lat=10.80, lng=106.70),
        Coordinate(lat=10.40, lng=107.05),
        START,
        True,
    )
    candidates = runner._candidates(trip, START, engine)
    assert [item.station_id for item in candidates] == ["S001"]
    assert calls == [(START, START)]  # True zero-distance ETA, not clipped to five minutes.
    for maximum in (0, -5, 7):
        with pytest.raises(ValueError, match="horizon"):
            DefaultSimulationRunner(
                lambda request: make_bundle(make_vehicles(1)),
                STATIONS,
                {Scenario.NORMAL: config},
                max_prediction_horizon_minutes=maximum,
            )

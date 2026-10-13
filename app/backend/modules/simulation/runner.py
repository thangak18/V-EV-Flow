"""Fair multi-strategy comparison on one pre-generated fixture bundle.

Each run builds a fresh engine from the immutable bundle and derives the same
vehicle trips from its seed, so strategies differ only in the station they
pick. Assumptions (all configurable): road distance = 1.3 x straight line,
50 km/h average speed, charge to 80% at 90% efficiency, drivers wait at most
30 minutes at a full station and never divert to the backup, and a driver who
ignores the suggestion (``1 - compliance_rate``) goes to the nearest station.

Not thread-safe: ``free_ports`` reflects the run in progress.
"""

import hashlib
import math
from collections import defaultdict, deque
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import Scenario, Strategy
from app.backend.contracts.ports import AllocationStrategy
from app.backend.contracts.recommendation import (
    AllocationContext,
    FeasibleCandidate,
    RecommendationRequest,
)
from app.backend.contracts.simulation import (
    FixtureBundle,
    ScenarioConfig,
    SimulationRequest,
    SimulationResult,
)
from app.backend.contracts.stations import Station
from app.backend.modules.simulation.baselines import (
    DEFAULT_MIN_SOC_PCT,
    CurrentlyAvailableStrategy,
    NearestStrategy,
)
from app.backend.modules.simulation.engine import SimulationEngine
from app.backend.modules.simulation.geo import road_km
from app.backend.modules.simulation.metrics import (
    OutcomeStatus,
    VehicleOutcome,
    calculate_metrics,
)
from app.backend.modules.simulation.trips import VehicleTrip, build_trips

AvailabilityFn = Callable[[str, datetime, datetime], float]
FixtureLoader = Callable[[SimulationRequest], FixtureBundle]
NOT_APPLICABLE = "not-applicable"


def bundle_hash(bundle: FixtureBundle) -> str:
    return hashlib.sha256(bundle.model_dump_json().encode("utf-8")).hexdigest()


class DefaultSimulationRunner:
    def __init__(
        self,
        fixture_loader: FixtureLoader,
        stations: Sequence[Station],
        configs: Mapping[Scenario, ScenarioConfig],
        availability: AvailabilityFn | None = None,
        min_soc_pct: float = DEFAULT_MIN_SOC_PCT,
        max_wait_minutes: float = 30.0,
        speed_kmh: float = 50.0,
        charge_to_pct: float = 80.0,
        charging_efficiency: float = 0.9,
    ) -> None:
        self._load = fixture_loader
        self._stations = tuple(stations)
        self._configs = dict(configs)
        self._availability = availability
        self._min_soc_pct = min_soc_pct
        self._max_wait = max_wait_minutes
        self._speed_kmh = speed_kmh
        self._charge_to_pct = charge_to_pct
        self._efficiency = charging_efficiency
        self._engine: SimulationEngine | None = None

    def free_ports(self, station_id: str) -> int:
        """Free ports right now in the run in progress."""
        if self._engine is None:
            raise RuntimeError("free_ports is only available while a run is in progress")
        return self._engine.free_ports(station_id)

    def baseline_strategies(self) -> dict[Strategy, AllocationStrategy]:
        return {
            Strategy.NEAREST: NearestStrategy(self._min_soc_pct),
            Strategy.CURRENTLY_AVAILABLE: CurrentlyAvailableStrategy(
                self.free_ports, self._min_soc_pct
            ),
        }

    def compare(
        self, request: SimulationRequest, strategies: Mapping[Strategy, AllocationStrategy]
    ) -> tuple[SimulationResult, ...]:
        return tuple(
            self.run(request.model_copy(update={"strategy": name}), strategy)
            for name, strategy in strategies.items()
        )

    def run(self, request: SimulationRequest, strategy: AllocationStrategy) -> SimulationResult:
        bundle = self._load(request)
        if bundle.scenario != request.scenario or bundle.seed != request.seed:
            raise ValueError("fixture bundle does not match the request scenario and seed")
        config = self._configs[request.scenario]
        trips = build_trips(bundle, config, request.vehicle_count)
        self._engine = SimulationEngine(
            self._stations,
            bundle.scenario,
            bundle.background_arrivals,
            bundle.service_durations,
            bundle.port_events,
        )
        try:
            outcomes = self._replay(self._engine, config, trips, strategy)
        finally:
            self._engine = None
        model_version = getattr(strategy, "model_version", None) or NOT_APPLICABLE
        return SimulationResult(
            scenario=request.scenario,
            seed=request.seed,
            strategy=request.strategy,
            model_version=str(model_version),
            metrics=calculate_metrics(outcomes, request.vehicle_count),
            fixture_hash=bundle_hash(bundle),
        )

    def _replay(
        self,
        engine: SimulationEngine,
        config: ScenarioConfig,
        trips: Sequence[VehicleTrip],
        strategy: AllocationStrategy,
    ) -> list[VehicleOutcome]:
        step = timedelta(minutes=config.step_minutes)
        by_station = {item.station_id: item for item in self._stations}
        fallback = NearestStrategy(self._min_soc_pct)
        departures = deque(trips)
        scheduled: dict[datetime, list[tuple[VehicleTrip, FeasibleCandidate]]] = defaultdict(list)
        waiting: dict[str, tuple[datetime, float]] = {}
        chosen_detour: dict[str, float] = {}
        outcomes: dict[str, VehicleOutcome] = {}

        def finish(vehicle_id: str, status: OutcomeStatus, **fields: float | str | None) -> None:
            outcomes[vehicle_id] = VehicleOutcome(vehicle_id, status, **fields)  # type: ignore[arg-type]

        ts = config.start
        while ts <= config.end:
            engine.step(ts)
            for vehicle_id, (arrived_at, detour) in list(waiting.items()):
                waited = (ts - arrived_at).total_seconds() / 60
                if engine.is_charging(vehicle_id):
                    finish(
                        vehicle_id,
                        OutcomeStatus.SERVED_AFTER_WAIT,
                        detour_km=detour,
                        wait_minutes=waited,
                    )
                elif waited >= self._max_wait:
                    engine.cancel(vehicle_id)
                    finish(
                        vehicle_id,
                        OutcomeStatus.FAILED,
                        detour_km=detour,
                        wait_minutes=self._max_wait,
                        reason="waited longer than the maximum wait",
                    )
                else:
                    continue
                del waiting[vehicle_id]
            for trip, candidate in scheduled.pop(ts, []):
                station = by_station[candidate.station_id]
                service = self._service_minutes(trip, candidate, station)
                if engine.arrive_now(trip.vehicle_id, station.station_id, service):
                    finish(
                        trip.vehicle_id,
                        OutcomeStatus.SUCCESS,
                        detour_km=candidate.detour_km,
                        wait_minutes=0.0,
                    )
                else:
                    waiting[trip.vehicle_id] = (ts, candidate.detour_km)
            while departures and departures[0].depart_at <= ts:
                trip = departures.popleft()
                candidates = self._candidates(trip, ts, engine)
                plan = None
                if candidates:
                    context = AllocationContext(
                        request=RecommendationRequest(
                            request_id=f"{config.scenario.value}-{config.seed}-{trip.vehicle_id}",
                            origin=trip.origin,
                            destination=trip.destination,
                            observed_at=ts,
                            depart_time=ts,
                            scenario=config.scenario,
                            vehicle=trip.vehicle,
                        ),
                        candidates=candidates,
                    )
                    plan = (strategy if trip.complies else fallback).select(context)
                if plan is None or plan.primary is None:
                    finish(
                        trip.vehicle_id, OutcomeStatus.FAILED, reason="no feasible station or plan"
                    )
                    continue
                chosen = next(
                    (c for c in candidates if c.station_id == plan.primary.station_id), None
                )
                if chosen is None:
                    finish(
                        trip.vehicle_id,
                        OutcomeStatus.FAILED,
                        reason="strategy chose a non-candidate station",
                    )
                    continue
                chosen_detour[trip.vehicle_id] = chosen.detour_km
                scheduled[self._arrival_step(config, ts, chosen.eta)].append((trip, chosen))
            ts += step

        for vehicle_id, (arrived_at, detour) in waiting.items():
            finish(
                vehicle_id,
                OutcomeStatus.FAILED,
                detour_km=detour,
                wait_minutes=(config.end - arrived_at).total_seconds() / 60,
                reason="window ended while waiting",
            )
        for trip in trips:
            if trip.vehicle_id not in outcomes:
                finish(
                    trip.vehicle_id,
                    OutcomeStatus.FAILED,
                    detour_km=chosen_detour.get(trip.vehicle_id),
                    reason="did not arrive before the window ended",
                )
        return [outcomes[trip.vehicle_id] for trip in trips]

    def _arrival_step(self, config: ScenarioConfig, now: datetime, eta: datetime) -> datetime:
        step = timedelta(minutes=config.step_minutes)
        steps = math.ceil((eta - config.start) / step)
        return max(config.start + steps * step, now + step)

    def _candidates(
        self, trip: VehicleTrip, now: datetime, engine: SimulationEngine
    ) -> tuple[FeasibleCandidate, ...]:
        direct = road_km(trip.origin, trip.destination)
        vehicle = trip.vehicle
        candidates = []
        for station in sorted(self._stations, key=lambda item: item.station_id):
            if vehicle.connector_type not in station.connector_types:
                continue
            place = Coordinate(lat=station.lat, lng=station.lng)
            distance = road_km(trip.origin, place)
            soc = (
                vehicle.soc_pct
                - 100 * distance * vehicle.consumption_kwh_per_km / vehicle.battery_kwh
            )
            if soc < self._min_soc_pct:
                continue
            eta = now + timedelta(hours=distance / self._speed_kmh)
            if self._availability is not None:
                probability = self._availability(station.station_id, now, eta)
            else:
                probability = 1.0 if engine.free_ports(station.station_id) > 0 else 0.0
            candidates.append(
                FeasibleCandidate(
                    station_id=station.station_id,
                    distance_km=distance,
                    detour_km=max(0.0, distance + road_km(place, trip.destination) - direct),
                    arrival_soc_pct=min(soc, 100.0),
                    p_available=probability,
                    eta=eta,
                )
            )
        return tuple(candidates)

    def _service_minutes(
        self, trip: VehicleTrip, candidate: FeasibleCandidate, station: Station
    ) -> float:
        needed_pct = max(0.0, self._charge_to_pct - candidate.arrival_soc_pct)
        kwh = trip.vehicle.battery_kwh * needed_pct / 100 / self._efficiency
        return min(120.0, max(10.0, kwh / station.power_kw * 60))


def compare_strategies(
    runner: DefaultSimulationRunner,
    request: SimulationRequest,
    strategies: Mapping[Strategy, AllocationStrategy],
) -> tuple[SimulationResult, ...]:
    return runner.compare(request, strategies)


def strategy_for(
    runner: DefaultSimulationRunner,
    name: Strategy,
    ai_strategy: AllocationStrategy | None = None,
) -> AllocationStrategy:
    """Map a ``Strategy`` enum to the strategy object a run should use.

    ``ai_allocation`` has no built-in implementation: the caller injects it, and
    a missing one is an error rather than a silent fallback to a baseline.
    """
    if name is Strategy.AI_ALLOCATION:
        if ai_strategy is None:
            raise ValueError("ai_allocation requires an injected AllocationStrategy")
        return ai_strategy
    return runner.baseline_strategies()[name]

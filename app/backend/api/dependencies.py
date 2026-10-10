"""Composition-root dependencies. Environment is read only by Settings/get_settings."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi import Request

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType
from app.backend.contracts.errors import RequestConflictError
from app.backend.contracts.ports import (
    AllocationStrategy,
    Predictor,
    RouteProvider,
    SimulationRunner,
    StationRepository,
    StatusRepository,
)
from app.backend.contracts.prediction import PredictRequest
from app.backend.contracts.recommendation import (
    AllocationContext,
    FeasibleCandidate,
    Plan,
    RecommendationRequest,
    RecommendationResult,
    RouteRequest,
)
from app.backend.core.settings import Settings
from app.backend.infrastructure.repositories.mock import MockStationRepository, MockStatusRepository
from app.backend.infrastructure.services.fakes import (
    FakeAllocationStrategy,
    FakePredictor,
    FakeRouteProvider,
    FakeSimulationRunner,
)
from app.backend.infrastructure.state.in_memory import InMemoryAllocationStore


class StartupConfigurationError(RuntimeError):
    """Raised when settings select an adapter unavailable in this phase."""


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    stations: StationRepository
    statuses: StatusRepository
    predictor: Predictor
    routes: RouteProvider
    allocation: AllocationStrategy
    simulation: SimulationRunner
    requests: InMemoryAllocationStore[Any]
    recommendation: "RecommendationFacade"

    @property
    def ready(self) -> bool:
        return True


def build_container(settings: Settings) -> AppContainer:
    if settings.data_backend != "mock":
        raise StartupConfigurationError(
            f"DATA_BACKEND={settings.data_backend} is unavailable in Phase 0"
        )
    if settings.predictor_backend != "fake":
        raise StartupConfigurationError(
            f"PREDICTOR_BACKEND={settings.predictor_backend} is unavailable in Phase 0"
        )
    if settings.route_backend != "fake":
        raise StartupConfigurationError(
            f"ROUTE_BACKEND={settings.route_backend} is unavailable in Phase 0"
        )
    stations = MockStationRepository(settings.data_dir / "fixtures" / "stations.json")
    container = AppContainer(
        settings=settings,
        stations=stations,
        statuses=MockStatusRepository(stations),
        predictor=FakePredictor(),
        routes=FakeRouteProvider(),
        allocation=FakeAllocationStrategy(),
        simulation=FakeSimulationRunner(),
        requests=InMemoryAllocationStore(),
        recommendation=None,  # type: ignore[arg-type]
    )
    container.recommendation = RecommendationFacade(container)
    return container


class RecommendationFacade:
    def __init__(self, container: AppContainer) -> None:
        self.container = container

    async def recommend(self, request: RecommendationRequest) -> RecommendationResult:
        existing = self.container.requests.get(request.request_id)
        fingerprint = request.model_dump(mode="json")
        if existing is not None:
            if existing["fingerprint"] != fingerprint:
                raise RequestConflictError(f"request_id already exists: {request.request_id}")
            return existing["result"]
        route = (
            await self.container.routes.get_routes(
                RouteRequest(
                    origin=request.origin,
                    destination=request.destination,
                    depart_time=request.depart_time,
                    vehicle=request.vehicle,
                )
            )
        )[0]
        candidates = []
        for station in self.container.stations.list_stations():
            station_route = (
                await self.container.routes.get_routes(
                    RouteRequest(
                        origin=request.origin,
                        destination=Coordinate(lat=station.lat, lng=station.lng),
                        depart_time=request.depart_time,
                        vehicle=request.vehicle,
                    )
                )
            )[0]
            eta = request.depart_time + timedelta(minutes=station_route.duration_minutes)
            prediction = self.container.predictor.predict(
                PredictRequest(
                    station_id=station.station_id,
                    observed_at=request.observed_at,
                    eta=eta,
                    connector_type=request.vehicle.connector_type,
                    scenario=request.scenario,
                )
            )
            energy_fraction = (
                station_route.distance_km
                * request.vehicle.consumption_kwh_per_km
                / request.vehicle.battery_kwh
            )
            candidates.append(
                FeasibleCandidate(
                    station_id=station.station_id,
                    distance_km=station_route.distance_km,
                    detour_km=abs(station_route.distance_km + 0.001 - route.distance_km),
                    arrival_soc_pct=max(0.0, request.vehicle.soc_pct - energy_fraction * 100),
                    p_available=prediction.p_available,
                    eta=eta,
                )
            )
        ranked = self.container.allocation.select(
            AllocationContext(request=request, candidates=tuple(candidates))
        )

        def plan(candidate):
            if candidate is None:
                return None
            payload = candidate.model_dump()
            payload.pop("rank", None)
            payload.pop("score", None)
            return Plan(**payload)

        result = RecommendationResult(
            request_id=request.request_id,
            primary=plan(ranked.primary),
            backup=plan(ranked.backup),
            plan_p=ranked.plan_p,
            plan_p_assumption=("independent_stations" if ranked.plan_p is not None else None),
            reasons=ranked.reasons,
            time_shift=None,
            model_version="fake-v1",
            allocation_method="nearest",
            data_type=DataType.MOCK,
        )
        self.container.requests.save(
            request.request_id, {"fingerprint": fingerprint, "result": result}
        )
        return result


def get_container(request: Request) -> AppContainer:
    return request.app.state.container

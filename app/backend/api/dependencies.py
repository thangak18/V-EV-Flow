"""Composition-root dependencies. Environment is read only by Settings/get_settings."""

from dataclasses import dataclass
from typing import Any

from fastapi import Request

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
from app.backend.contracts.recommendation import (
    RecommendationRequest,
    RecommendationResult,
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
        result = RecommendationResult(
            request_id=request.request_id,
            primary=None,
            backup=None,
            plan_p=None,
            plan_p_assumption=None,
            reasons=["Phase 0 placeholder: recommendation ranking is not implemented."],
            time_shift=None,
            model_version="fake-v1",
            allocation_method="phase0_placeholder",
            data_type=DataType.MOCK,
        )
        stored, created = self.container.requests.get_or_create(
            request.request_id, lambda: {"fingerprint": fingerprint, "result": result}
        )
        if not created and stored["fingerprint"] != fingerprint:
            raise RequestConflictError(f"request_id already exists: {request.request_id}")
        return stored["result"]


def get_container(request: Request) -> AppContainer:
    return request.app.state.container

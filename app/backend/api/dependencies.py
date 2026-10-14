"""Composition-root dependencies. Environment is read only by Settings/get_settings."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import Request

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import DataSourceUnavailableError, RequestConflictError
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
from app.backend.infrastructure.repositories.files import (
    FileStationRepository,
    ParquetStatusRepository,
)
from app.backend.infrastructure.repositories.mock import MockStationRepository, MockStatusRepository
from app.backend.infrastructure.routing.cache import RouteCache
from app.backend.infrastructure.routing.goong import GoongRouteProvider
from app.backend.infrastructure.services.fakes import (
    FakeAllocationStrategy,
    FakePredictor,
    FakeRouteProvider,
    FakeSimulationRunner,
)
from app.backend.infrastructure.state.in_memory import InMemoryAllocationStore
from app.backend.infrastructure.state.virtual_load import VirtualLoadStore
from app.backend.modules.recommendation.allocation import AllocationCoordinator
from app.backend.modules.recommendation.ranking import RankingConfig
from app.backend.modules.recommendation.service import RecommendationService


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
    status_repositories_by_scenario: Mapping[Scenario, StatusRepository]
    predictors_by_scenario: Mapping[Scenario, Predictor]
    ranking_config: RankingConfig
    virtual_load_store: VirtualLoadStore
    allocation_coordinator: AllocationCoordinator
    owned_route_client: httpx.AsyncClient | None = None

    async def close(self) -> None:
        if self.owned_route_client is not None and not self.owned_route_client.is_closed:
            await self.owned_route_client.aclose()

    @property
    def ready(self) -> bool:
        return True


def build_container(
    settings: Settings, *, route_client: httpx.AsyncClient | None = None
) -> AppContainer:
    if settings.data_backend == "real":
        raise StartupConfigurationError("DATA_BACKEND=real has no approved adapter")
    if settings.predictor_backend != "fake":
        raise StartupConfigurationError(
            f"PREDICTOR_BACKEND={settings.predictor_backend} is unavailable in Phase 0"
        )
    stations = _build_station_repository(settings)
    statuses = _build_status_repositories(settings, stations)
    predictors = _build_predictors(settings)
    ranking = RankingConfig(min_arrival_soc_pct=settings.min_arrival_soc_pct)
    store = VirtualLoadStore(ttl=timedelta(seconds=settings.virtual_load_receipt_ttl_seconds))
    routes, owned_route_client = _build_route_provider(settings, route_client=route_client)

    def service_factory(reader: VirtualLoadStore) -> RecommendationService:
        return RecommendationService(
            station_repository=stations,
            status_repositories=statuses,
            route_provider=routes,
            predictors=predictors,
            ranking_config=ranking,
            data_type=_recommendation_data_type(settings),
            max_prediction_horizon_minutes={
                scenario: settings.fake_prediction_horizon_minutes for scenario in Scenario
            },
            virtual_load_provider=reader,
        )

    coordinator = AllocationCoordinator(
        store=store,
        service_factory=service_factory,
        charge_duration_minutes=settings.assumed_charge_duration_minutes,
        expected_load=settings.expected_virtual_load,
    )
    container = AppContainer(
        settings=settings,
        stations=stations,
        statuses=statuses[Scenario.NORMAL],
        predictor=predictors[Scenario.NORMAL],
        routes=routes,
        allocation=FakeAllocationStrategy(),
        simulation=_build_simulation_runner(settings),
        requests=InMemoryAllocationStore(),
        recommendation=None,  # type: ignore[arg-type]
        status_repositories_by_scenario=statuses,
        predictors_by_scenario=predictors,
        ranking_config=ranking,
        virtual_load_store=store,
        allocation_coordinator=coordinator,
        owned_route_client=owned_route_client,
    )
    container.recommendation = RecommendationFacade(container)
    return container


def _build_station_repository(settings: Settings) -> StationRepository:
    if settings.data_backend == "mock":
        return MockStationRepository(settings.data_dir / "fixtures" / "stations.json")
    if settings.data_backend == "file":
        try:
            return FileStationRepository(settings.data_dir / "generated" / "stations.json")
        except (DataSourceUnavailableError, OSError, ValueError) as exc:
            raise StartupConfigurationError(
                "file station metadata is unavailable or invalid"
            ) from exc
    raise StartupConfigurationError("DATA_BACKEND=real has no approved adapter")


def _build_status_repositories(
    settings: Settings, stations: StationRepository
) -> dict[Scenario, StatusRepository]:
    if settings.data_backend == "mock":
        return {scenario: MockStatusRepository(stations, scenario) for scenario in Scenario}  # type: ignore[arg-type]
    path = settings.data_dir / "generated" / "station_status.parquet"
    return {scenario: ParquetStatusRepository(path, stations, scenario) for scenario in Scenario}


def _build_predictors(settings: Settings) -> dict[Scenario, Predictor]:
    if settings.predictor_backend != "fake":
        raise StartupConfigurationError("PREDICTOR_BACKEND=model has no approved C7 integration")
    return {scenario: FakePredictor() for scenario in Scenario}


def _build_simulation_runner(settings: Settings) -> SimulationRunner:
    return FakeSimulationRunner()


def _recommendation_data_type(settings: Settings) -> DataType:
    return DataType.SIMULATED if settings.data_backend == "file" else DataType.MOCK


def _build_route_provider(
    settings: Settings, *, route_client: httpx.AsyncClient | None = None
) -> tuple[RouteProvider, httpx.AsyncClient | None]:
    if settings.route_backend == "fake":
        return FakeRouteProvider(), None
    if not settings.goong_rest_api_key:
        raise StartupConfigurationError("ROUTE_BACKEND=goong requires GOONG_REST_API_KEY")
    client = route_client or httpx.AsyncClient()
    return GoongRouteProvider(
        settings.goong_rest_api_key,
        client,
        RouteCache(settings.goong_cache_dir, timedelta(seconds=settings.goong_cache_ttl_seconds)),
        clock=lambda: datetime.now(UTC),
    ), (client if route_client is None else None)


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

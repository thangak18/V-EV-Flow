"""Composition-root dependencies. Environment is read only by Settings/get_settings."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import Request

from app.backend.api.runtime import RuntimePredictor, StatefulSimulation
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import DataSourceUnavailableError, RequestConflictError
from app.backend.contracts.ports import (
    AllocationStrategy,
    Predictor,
    QueueObservationSource,
    RouteProvider,
    SimulationRunner,
    StationRepository,
    StatusRepository,
    WhatIfRunner,
)
from app.backend.contracts.recommendation import (
    RecommendationRequest,
    RecommendationResult,
)
from app.backend.core.settings import Settings
from app.backend.infrastructure.locations.goong import GoongPlaces
from app.backend.infrastructure.repositories.files import (
    FileStationRepository,
    ParquetStatusRepository,
)
from app.backend.infrastructure.repositories.mock import MockStationRepository, MockStatusRepository
from app.backend.infrastructure.repositories.partner import PartnerHistory, PartnerStatusRepository
from app.backend.infrastructure.routing.cache import RouteCache
from app.backend.infrastructure.routing.goong import GoongRouteProvider
from app.backend.infrastructure.services.camera_mock import MockCameraQueueSource
from app.backend.infrastructure.services.fakes import (
    FakeAllocationStrategy,
    FakePredictor,
    FakeRouteProvider,
    FakeSimulationRunner,
)
from app.backend.infrastructure.state.in_memory import InMemoryAllocationStore
from app.backend.infrastructure.state.sqlite import SQLiteVirtualLoadStore
from app.backend.infrastructure.state.virtual_load import VirtualLoadStore
from app.backend.modules.prediction.public import load_predictor, read_manifest
from app.backend.modules.recommendation.allocation import AllocationCoordinator
from app.backend.modules.recommendation.ranking import RankingConfig
from app.backend.modules.recommendation.service import RecommendationService, VirtualLoadReader


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
    whatif_simulation: WhatIfRunner | None
    requests: InMemoryAllocationStore[Any]
    recommendation: "RecommendationFacade"
    status_repositories_by_scenario: Mapping[Scenario, StatusRepository]
    predictors_by_scenario: Mapping[Scenario, Predictor]
    ranking_config: RankingConfig
    prediction_horizons: Mapping[Scenario, int]
    virtual_load_store: VirtualLoadStore | SQLiteVirtualLoadStore
    allocation_coordinator: AllocationCoordinator
    queue_source: QueueObservationSource | None = None
    owned_route_client: httpx.AsyncClient | None = None
    places: GoongPlaces | None = None
    owned_places_client: httpx.AsyncClient | None = None
    partner_history: PartnerHistory | None = None

    async def close(self) -> None:
        if self.owned_places_client is not None:
            await self.owned_places_client.aclose()
        if self.owned_route_client is not None and not self.owned_route_client.is_closed:
            await self.owned_route_client.aclose()

    @property
    def ready(self) -> bool:
        return True


def _build_queue_source(
    settings: Settings, stations: StationRepository
) -> QueueObservationSource | None:
    if settings.camera_queue_backend == "off":
        return None
    return MockCameraQueueSource(
        stations.list_stations(), config_path=settings.camera_queue_config_path
    )


def build_container(
    settings: Settings, *, route_client: httpx.AsyncClient | None = None
) -> AppContainer:
    stations = _build_station_repository(settings)
    statuses = _build_status_repositories(settings, stations)
    try:
        predictors, horizons = _build_predictors(settings, statuses, stations)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise StartupConfigurationError("model artifact is unavailable or incompatible") from exc
    ranking = RankingConfig(min_arrival_soc_pct=settings.min_arrival_soc_pct)
    ttl = timedelta(seconds=settings.virtual_load_receipt_ttl_seconds)
    store = (
        SQLiteVirtualLoadStore(settings.allocation_db_path, ttl=ttl)
        if settings.allocation_backend == "sqlite"
        else VirtualLoadStore(ttl=ttl)
    )
    routes, owned_route_client = _build_route_provider(settings, route_client=route_client)
    queue_source = _build_queue_source(settings, stations)

    def service_factory(reader: VirtualLoadReader) -> RecommendationService:
        return RecommendationService(
            station_repository=stations,
            status_repositories=statuses,
            route_provider=routes,
            predictors=predictors,
            ranking_config=ranking,
            data_type=_recommendation_data_type(settings),
            max_prediction_horizon_minutes=horizons,
            virtual_load_provider=reader,
            queue_source=queue_source,
            time_shift_minutes=(15, 30) if settings.time_shift_suggestions else (),
        )

    try:
        simulation = _build_simulation_runner(settings, stations, ranking, min(horizons.values()))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise StartupConfigurationError(
            "simulation fixtures/configuration are unavailable or invalid"
        ) from exc
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
        simulation=simulation,
        whatif_simulation=simulation if isinstance(simulation, StatefulSimulation) else None,
        requests=InMemoryAllocationStore(),
        recommendation=None,  # type: ignore[arg-type]
        status_repositories_by_scenario=statuses,
        predictors_by_scenario=predictors,
        ranking_config=ranking,
        prediction_horizons=horizons,
        virtual_load_store=store,
        allocation_coordinator=coordinator,
        queue_source=queue_source,
        owned_route_client=owned_route_client,
    )
    if settings.places_backend == "goong" and settings.goong_rest_api_key:
        places_client = route_client or httpx.AsyncClient()
        container.places = GoongPlaces(settings.goong_rest_api_key, places_client)
        container.owned_places_client = None if route_client is not None else places_client
    if settings.data_backend == "real":
        container.partner_history = PartnerHistory(
            settings.partner_history_path, stations, settings.partner_source or ""
        )
    container.recommendation = RecommendationFacade(container)
    return container


def _build_station_repository(settings: Settings) -> StationRepository:
    if settings.data_backend == "mock":
        return MockStationRepository(settings.data_dir / "fixtures" / "stations.json")
    if settings.data_backend in ("file", "real"):
        try:
            repository = FileStationRepository(settings.data_dir / "generated" / "stations.json")
            if settings.data_backend == "real" and any(
                station.source != settings.partner_source for station in repository.list_stations()
            ):
                raise ValueError(
                    "real station metadata must identify the configured partner source"
                )
            return repository
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
    if settings.data_backend == "real":
        history = PartnerHistory(
            settings.partner_history_path, stations, settings.partner_source or ""
        )
        return {scenario: PartnerStatusRepository(history, scenario) for scenario in Scenario}
    path = settings.data_dir / "generated" / "station_status.parquet"
    return {
        scenario: ParquetStatusRepository(
            path, stations, scenario, allow_missing_lags=settings.predictor_backend == "model"
        )
        for scenario in Scenario
    }


def _build_predictors(
    settings: Settings,
    statuses: Mapping[Scenario, StatusRepository],
    stations: StationRepository,
) -> tuple[dict[Scenario, Predictor], dict[Scenario, int]]:
    if settings.predictor_backend == "fake":
        return (
            {scenario: FakePredictor() for scenario in Scenario},
            {scenario: settings.fake_prediction_horizon_minutes for scenario in Scenario},
        )
    manifest = read_manifest(settings.model_dir)
    if set(manifest.scenarios) != {scenario.value for scenario in Scenario}:
        raise ValueError("model artifact must support all configured scenarios")
    maximum = manifest.split_metadata["max_horizon_minutes"]
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 30 or maximum % 5:
        raise ValueError("model horizon must support the 30-minute pressure proxy")
    predictors: dict[Scenario, Predictor] = {
        scenario: RuntimePredictor(
            load_predictor(
                settings.model_dir,
                statuses[scenario],
                stations,
                status_data_type=DataType.REAL
                if settings.data_backend == "real"
                else DataType.SIMULATED,
                explain=settings.prediction_explanations,
            )
        )
        for scenario in Scenario
    }
    return predictors, {scenario: maximum for scenario in Scenario}


def _build_simulation_runner(
    settings: Settings, stations: StationRepository, ranking: RankingConfig, maximum_horizon: int
) -> SimulationRunner:
    if settings.simulation_backend == "fake":
        return FakeSimulationRunner()
    return StatefulSimulation(
        stations=stations,
        model_dir=settings.model_dir,
        generated_dir=settings.data_dir / "generated",
        scenarios_path=settings.simulation_scenarios_path,
        ranking=ranking,
        maximum_horizon=maximum_horizon,
        duration=settings.assumed_charge_duration_minutes,
        load=settings.expected_virtual_load,
        capacity_models_dir=settings.capacity_models_dir,
    )


def _recommendation_data_type(settings: Settings) -> DataType:
    return (
        DataType.REAL
        if settings.data_backend == "real"
        else DataType.SIMULATED
        if settings.data_backend == "file"
        else DataType.MOCK
    )


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
        retries=1,
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

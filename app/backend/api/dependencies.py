"""Composition-root dependencies. Environment is read only by Settings/get_settings."""

from dataclasses import dataclass
from typing import Any

from fastapi import Request

from app.backend.contracts.ports import (
    AllocationStrategy,
    Predictor,
    RouteProvider,
    SimulationRunner,
    StationRepository,
    StatusRepository,
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
    return AppContainer(
        settings=settings,
        stations=stations,
        statuses=MockStatusRepository(stations),
        predictor=FakePredictor(),
        routes=FakeRouteProvider(),
        allocation=FakeAllocationStrategy(),
        simulation=FakeSimulationRunner(),
        requests=InMemoryAllocationStore(),
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container

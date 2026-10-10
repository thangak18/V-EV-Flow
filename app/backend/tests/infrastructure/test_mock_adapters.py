from datetime import UTC, datetime

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType, Scenario, Strategy
from app.backend.contracts.prediction import PredictRequest
from app.backend.contracts.recommendation import (
    AllocationContext,
    FeasibleCandidate,
    RecommendationRequest,
    Vehicle,
)
from app.backend.contracts.simulation import SimulationRequest
from app.backend.infrastructure.repositories.mock import MockStationRepository, MockStatusRepository
from app.backend.infrastructure.services.fakes import (
    FakeAllocationStrategy,
    FakePredictor,
    FakeRouteProvider,
    FakeSimulationRunner,
)
from app.backend.tests.conformance.repository_contract import StationRepositoryContract


class TestMockStationRepository(StationRepositoryContract):
    def make_repository(self):
        return MockStationRepository()


def test_predictor_is_deterministic_and_mock_labelled() -> None:
    request = PredictRequest(
        station_id="S001",
        observed_at=datetime(2026, 10, 13, tzinfo=UTC),
        eta=datetime(2026, 10, 13, 1, tzinfo=UTC),
        connector_type="CCS2",
        scenario=Scenario.NORMAL,
    )
    result = FakePredictor().predict(request)
    assert result.p_available == 0.75
    assert result.data_type is DataType.MOCK


def test_status_repository_returns_requested_lags() -> None:
    observed = datetime(2026, 10, 13, tzinfo=UTC)
    result = MockStatusRepository().window("S001", observed, (15, 30))
    assert result.station_id == "S001"
    assert result.lags == (15, 30)
    assert all(item.station_id == "S001" for item in result.statuses)


def test_route_and_strategy_are_deterministic() -> None:
    vehicle = Vehicle(soc_pct=20, battery_kwh=60, consumption_kwh_per_km=0.2, connector_type="CCS2")
    request = RecommendationRequest(
        request_id="r1",
        origin=Coordinate(lat=10.7, lng=106.6),
        destination=Coordinate(lat=10.8, lng=106.8),
        observed_at=datetime(2026, 10, 13, tzinfo=UTC),
        depart_time=datetime(2026, 10, 13, tzinfo=UTC),
        scenario=Scenario.NORMAL,
        vehicle=vehicle,
    )
    route_request = __import__(
        "app.backend.contracts.recommendation", fromlist=["RouteRequest"]
    ).RouteRequest(
        origin=request.origin,
        destination=request.destination,
        depart_time=request.depart_time,
        vehicle=vehicle,
    )
    import asyncio

    route = asyncio.run(FakeRouteProvider().get_routes(route_request))[0]
    assert route.distance_km > 0
    candidates = tuple(
        FeasibleCandidate(
            station_id=x,
            distance_km=d,
            detour_km=0,
            arrival_soc_pct=50,
            p_available=0.75,
            eta=request.depart_time,
        )
        for x, d in (("S001", 3.0), ("S002", 8.0))
    )
    ranked = FakeAllocationStrategy().select(
        AllocationContext(request=request, candidates=candidates)
    )
    assert ranked.primary and ranked.primary.station_id == "S001"


def test_simulation_runner_is_reproducible() -> None:
    request = SimulationRequest(
        scenario=Scenario.NORMAL, seed=42, vehicle_count=10, strategy=Strategy.NEAREST
    )
    runner = FakeSimulationRunner()
    first = runner.run(request, FakeAllocationStrategy())
    second = runner.run(request, FakeAllocationStrategy())
    assert first == second
    assert len(first.fixture_hash) == 64

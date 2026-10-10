import hashlib
import math

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType
from app.backend.contracts.ports import AllocationStrategy
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import (
    AllocationContext,
    RankedCandidate,
    RankedPlan,
    RouteRequest,
    RouteResult,
)
from app.backend.contracts.simulation import SimulationMetrics, SimulationRequest, SimulationResult


class FakePredictor:
    def predict(self, request: PredictRequest) -> PredictionResult:
        return PredictionResult(
            station_id=request.station_id,
            eta=request.eta,
            p_available=0.75,
            reasons=["Phase 0 deterministic mock prediction"],
            explanation_method="rule",
            model_version="fake-v1",
            data_type=DataType.MOCK,
            contract_version="0.1.0",
        )


class FakeRouteProvider:
    async def get_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]:
        distance = _distance(request.origin, request.destination)
        duration = distance / 40.0 * 60.0
        geometry = (request.origin, request.destination)
        return (
            RouteResult(
                distance_km=round(distance, 3),
                duration_minutes=round(duration, 3),
                geometry=geometry,
                source="mock",
            ),
        )


class FakeAllocationStrategy:
    def select(self, context: AllocationContext) -> RankedPlan:
        ordered = sorted(context.candidates, key=lambda item: (item.distance_km, item.station_id))
        ranked = [
            RankedCandidate(**candidate.model_dump(), rank=index, score=1 / index)
            for index, candidate in enumerate(ordered, 1)
        ]
        return RankedPlan(
            primary=ranked[0] if ranked else None,
            backup=ranked[1] if len(ranked) > 1 else None,
            plan_p=ranked[0].p_available if ranked else None,
            reasons=["Phase 0 deterministic nearest-station allocation"],
        )


class FakeSimulationRunner:
    def run(self, request: SimulationRequest, strategy: AllocationStrategy) -> SimulationResult:
        payload = (
            f"phase0-fixture|{request.scenario.value}|{request.seed}|{request.vehicle_count}"
        ).encode()
        fixture_hash = hashlib.sha256(payload).hexdigest()
        failed = request.vehicle_count // 10
        metrics = SimulationMetrics(
            success_rate=(request.vehicle_count - failed) / request.vehicle_count,
            mean_detour_km=2.5,
            mean_wait_minutes=4.0,
            failed_count=failed,
            vehicle_count=request.vehicle_count,
        )
        return SimulationResult(
            scenario=request.scenario,
            seed=request.seed,
            strategy=request.strategy,
            model_version="fake-sim-v1",
            metrics=metrics,
            fixture_hash=fixture_hash,
        )


def _distance(origin: Coordinate, destination: Coordinate) -> float:
    radius = 6371.0
    lat1, lat2 = math.radians(origin.lat), math.radians(destination.lat)
    dlat = lat2 - lat1
    dlng = math.radians(destination.lng - origin.lng)
    hav = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(hav))

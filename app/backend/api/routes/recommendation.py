from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.api.errors import FeatureNotReadyError
from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import RequestConflictError
from app.backend.contracts.prediction import PredictRequest
from app.backend.contracts.recommendation import (
    AllocationContext,
    FeasibleCandidate,
    Plan,
    PressureResponse,
    PressureStation,
    RecommendationRequest,
    RecommendationResult,
    RouteRequest,
)
from app.backend.contracts.simulation import (
    ResetRequest,
    ResetResponse,
    SimulationRequest,
    SimulationResult,
)

router = APIRouter()


@router.post("/recommend", response_model=RecommendationResult, operation_id="recommendStation")
async def recommend(
    request: RecommendationRequest, container: AppContainer = Depends(get_container)
) -> RecommendationResult:
    existing = container.requests.get(request.request_id)
    fingerprint = request.model_dump(mode="json")
    if existing is not None:
        if existing["fingerprint"] != fingerprint:
            raise RequestConflictError(f"request_id already exists: {request.request_id}")
        return existing["result"]
    route = (await container.routes.get_routes(RouteRequest(
        origin=request.origin, destination=request.destination,
        depart_time=request.depart_time, vehicle=request.vehicle,
    )))[0]
    candidates = []
    for station in container.stations.list_stations():
        station_route = (await container.routes.get_routes(RouteRequest(
            origin=request.origin, destination=Coordinate(lat=station.lat, lng=station.lng),
            depart_time=request.depart_time, vehicle=request.vehicle,
        )))[0]
        eta = request.depart_time + timedelta(minutes=station_route.duration_minutes)
        prediction = container.predictor.predict(PredictRequest(
            station_id=station.station_id, observed_at=request.observed_at, eta=eta,
            connector_type=request.vehicle.connector_type, scenario=request.scenario,
        ))
        energy_fraction = (
            station_route.distance_km
            * request.vehicle.consumption_kwh_per_km
            / request.vehicle.battery_kwh
        )
        arrival_soc = max(0.0, request.vehicle.soc_pct - energy_fraction * 100)
        candidates.append(FeasibleCandidate(
            station_id=station.station_id, distance_km=station_route.distance_km,
            detour_km=abs(station_route.distance_km + 0.001 - route.distance_km),
            arrival_soc_pct=arrival_soc, p_available=prediction.p_available, eta=eta,
        ))
    ranked = container.allocation.select(
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
        request_id=request.request_id, primary=plan(ranked.primary), backup=plan(ranked.backup),
        plan_p=ranked.plan_p,
        plan_p_assumption=("independent_stations" if ranked.plan_p is not None else None),
        reasons=ranked.reasons, time_shift=None, model_version="fake-v1",
        allocation_method="nearest", data_type=DataType.MOCK,
    )
    container.requests.save(request.request_id, {"fingerprint": fingerprint, "result": result})
    return result


@router.get("/pressure", response_model=PressureResponse, operation_id="getPressure")
def pressure(
    scenario: Scenario = Query(...),
    time: datetime = Query(...),
    container: AppContainer = Depends(get_container),
) -> PressureResponse:
    stations = tuple(PressureStation(
        station_id=station.station_id,
        p_available=0.75,
        pressure_score=0.25,
        data_type=DataType.MOCK,
    ) for station in container.stations.list_stations())
    return PressureResponse(time=time, scenario=scenario, stations=stations)


@router.post("/simulate", response_model=SimulationResult, operation_id="simulate")
def simulate(
    request: SimulationRequest, container: AppContainer = Depends(get_container)
) -> SimulationResult:
    return container.simulation.run(request, container.allocation)


@router.post("/whatif", status_code=503, operation_id="whatIf")
def whatif() -> None:
    raise FeatureNotReadyError("what-if is planned for P1")


@router.post("/reset", response_model=ResetResponse, operation_id="resetDemo")
def reset(request: ResetRequest, container: AppContainer = Depends(get_container)) -> ResetResponse:
    del request
    container.requests.reset()
    return ResetResponse(reset=True)

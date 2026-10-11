from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.api.errors import FeatureNotReadyError
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import ErrorResponse
from app.backend.contracts.recommendation import (
    PressureResponse,
    PressureStation,
    RecommendationRequest,
    RecommendationResult,
)
from app.backend.contracts.simulation import (
    ResetRequest,
    ResetResponse,
    SimulationRequest,
    SimulationResult,
)

router = APIRouter()


@router.post(
    "/recommend",
    response_model=RecommendationResult,
    operation_id="recommendStation",
    responses={409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def recommend(
    request: RecommendationRequest, container: AppContainer = Depends(get_container)
) -> RecommendationResult:
    return await container.recommendation.recommend(request)


@router.get("/pressure", response_model=PressureResponse, operation_id="getPressure")
def pressure(
    scenario: Scenario = Query(...),
    time: datetime = Query(...),
    container: AppContainer = Depends(get_container),
) -> PressureResponse:
    stations = tuple(
        PressureStation(
            station_id=station.station_id,
            p_available=0.75,
            pressure_score=0.25,
            data_type=DataType.MOCK,
        )
        for station in container.stations.list_stations()
    )
    return PressureResponse(time=time, scenario=scenario, stations=stations)


@router.post("/simulate", response_model=SimulationResult, operation_id="simulate")
def simulate(
    request: SimulationRequest, container: AppContainer = Depends(get_container)
) -> SimulationResult:
    return container.simulation.run(request, container.allocation)


@router.post(
    "/whatif",
    response_model=ErrorResponse,
    status_code=503,
    operation_id="whatIf",
    responses={503: {"model": ErrorResponse}},
)
def whatif() -> None:
    raise FeatureNotReadyError("what-if is planned for P1")


@router.post("/reset", response_model=ResetResponse, operation_id="resetDemo")
def reset(request: ResetRequest, container: AppContainer = Depends(get_container)) -> ResetResponse:
    del request
    container.requests.reset()
    return ResetResponse(reset=True)

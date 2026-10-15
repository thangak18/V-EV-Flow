from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.api.errors import FeatureNotReadyError
from app.backend.api.validation import (
    validate_live_observation,
    validate_prediction_result,
    validate_recommendation_request,
)
from app.backend.contracts.enums import Scenario
from app.backend.contracts.errors import ErrorResponse
from app.backend.contracts.prediction import PredictRequest
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
    WhatIfRequest,
    WhatIfResult,
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
    validate_live_observation(container, request.observed_at)
    validate_recommendation_request(request)
    return await container.allocation_coordinator.recommend(request)


@router.get("/pressure", response_model=PressureResponse, operation_id="getPressure")
def pressure(
    scenario: Scenario = Query(...),
    time: datetime = Query(...),
    container: AppContainer = Depends(get_container),
) -> PressureResponse:
    validate_live_observation(container, time)
    horizon_minutes = container.prediction_horizons[scenario]
    if horizon_minutes < 30:
        raise ValueError("configured prediction horizon does not support pressure proxy")
    eta = time + timedelta(minutes=30)
    if time.utcoffset() != timedelta(hours=7) or time.minute % 5 or time.second or time.microsecond:
        from fastapi import HTTPException

        raise HTTPException(422, "time must use a +07:00 five-minute bucket")
    predictor = container.predictors_by_scenario[scenario]
    stations = tuple(
        _pressure_station(station, scenario, time, eta, predictor)
        for station in container.stations.list_stations()
    )
    return PressureResponse(time=time, scenario=scenario, stations=stations)


def _pressure_station(station, scenario: Scenario, observed_at: datetime, eta: datetime, predictor):
    predict_request = PredictRequest(
        station_id=station.station_id,
        observed_at=observed_at,
        eta=eta,
        connector_type=station.connector_types[0],
        scenario=scenario,
    )
    prediction = validate_prediction_result(predict_request, predictor.predict(predict_request))
    return PressureStation(
        station_id=station.station_id,
        p_available=prediction.p_available,
        pressure_score=1 - prediction.p_available,
        data_type=prediction.data_type,
    )


@router.post("/simulate", response_model=SimulationResult, operation_id="simulate")
def simulate(
    request: SimulationRequest, container: AppContainer = Depends(get_container)
) -> SimulationResult:
    if container.settings.simulation_backend == "stateful" and request.seed < 0:
        raise HTTPException(422, "stateful simulation requires a nonnegative seed")
    return container.simulation.run(request, container.allocation)


@router.post(
    "/whatif",
    response_model=WhatIfResult,
    operation_id="whatIf",
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def whatif(
    request: WhatIfRequest | None = None, container: AppContainer = Depends(get_container)
) -> WhatIfResult:
    if request is None:
        raise FeatureNotReadyError("what-if requires an explicit experiment request")
    if container.whatif_simulation is None:
        raise FeatureNotReadyError("what-if requires file/model/stateful mode")
    if request.seed < 0:
        raise HTTPException(422, "what-if requires a nonnegative seed")
    return container.whatif_simulation.run_whatif(request)


@router.post("/reset", response_model=ResetResponse, operation_id="resetDemo")
async def reset(
    request: ResetRequest, container: AppContainer = Depends(get_container)
) -> ResetResponse:
    del request
    await container.allocation_coordinator.reset()
    container.requests.reset()
    return ResetResponse(reset=True)

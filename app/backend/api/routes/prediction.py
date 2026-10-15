from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.api.validation import validate_predict_request, validate_prediction_result
from app.backend.contracts.errors import ErrorResponse, StationNotFoundError
from app.backend.contracts.prediction import PredictionResult, PredictRequest

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictionResult,
    operation_id="predictAvailability",
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def predict(
    request: PredictRequest, container: AppContainer = Depends(get_container)
) -> PredictionResult:
    try:
        station = container.stations.get_station(request.station_id)
    except KeyError as exc:
        raise StationNotFoundError(f"Unknown station: {request.station_id}") from exc
    validate_predict_request(request, container.prediction_horizons[request.scenario])
    if request.connector_type not in station.connector_types:
        raise HTTPException(422, "connector_type is not supported by the station")
    result = container.predictors_by_scenario[request.scenario].predict(request)
    return validate_prediction_result(request, result)

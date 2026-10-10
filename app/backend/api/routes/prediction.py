from fastapi import APIRouter, Depends

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.contracts.errors import StationNotFoundError
from app.backend.contracts.prediction import PredictionResult, PredictRequest

router = APIRouter()


@router.post("/predict", response_model=PredictionResult, operation_id="predictAvailability")
def predict(
    request: PredictRequest, container: AppContainer = Depends(get_container)
) -> PredictionResult:
    try:
        container.stations.get_station(request.station_id)
    except KeyError as exc:
        raise StationNotFoundError(f"Unknown station: {request.station_id}") from exc
    return container.predictor.predict(request)

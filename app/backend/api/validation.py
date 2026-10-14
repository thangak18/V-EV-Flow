from datetime import datetime, timedelta

from fastapi import HTTPException

from app.backend.contracts.errors import DataSourceUnavailableError
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import RecommendationRequest

OFFSET = timedelta(hours=7)


def _aligned(value: datetime) -> bool:
    return (
        value.utcoffset() == OFFSET
        and value.minute % 5 == 0
        and value.second == 0
        and value.microsecond == 0
    )


def validate_predict_request(request: PredictRequest, maximum_horizon: int) -> None:
    if not _aligned(request.observed_at) or not _aligned(request.eta):
        raise HTTPException(422, "timestamps must use +07:00 five-minute buckets")
    seconds = (request.eta - request.observed_at).total_seconds()
    if seconds <= 0 or seconds % 300 or seconds > maximum_horizon * 60:
        raise HTTPException(422, "prediction horizon is outside the configured capability")


def validate_recommendation_request(request: RecommendationRequest) -> None:
    if not _aligned(request.observed_at) or request.depart_time.utcoffset() != OFFSET:
        raise HTTPException(422, "timestamps must use the +07:00 convention")
    if request.depart_time < request.observed_at:
        raise HTTPException(422, "depart_time must not precede observed_at")


def validate_prediction_result(
    request: PredictRequest, result: PredictionResult
) -> PredictionResult:
    try:
        checked = PredictionResult.model_validate(result.model_dump(mode="json"))
    except Exception as exc:
        raise DataSourceUnavailableError("predictor returned an invalid response") from exc
    if checked.station_id != request.station_id or checked.eta != request.eta:
        raise DataSourceUnavailableError("predictor response does not match the request")
    return checked

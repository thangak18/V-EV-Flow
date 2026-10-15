from datetime import datetime, timedelta
from math import isfinite

from fastapi import HTTPException

from app.backend.contracts.errors import DataSourceUnavailableError, ModelNotReadyError
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
    nonfinite = [
        name
        for name, value in (
            ("origin.lat", request.origin.lat),
            ("origin.lng", request.origin.lng),
            ("destination.lat", request.destination.lat),
            ("destination.lng", request.destination.lng),
            ("vehicle.soc_pct", request.vehicle.soc_pct),
            ("vehicle.battery_kwh", request.vehicle.battery_kwh),
            ("vehicle.consumption_kwh_per_km", request.vehicle.consumption_kwh_per_km),
        )
        if not isfinite(value)
    ]
    if nonfinite:
        raise HTTPException(422, f"non-finite numeric values are not accepted: {nonfinite}")


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


def validate_live_observation(container, observed_at: datetime) -> None:
    """Never disguise old snapshots or holiday simulations as current live occupancy."""
    if container.settings.data_backend != "real":
        return
    from datetime import UTC

    from app.backend.contracts.errors import DataSourceUnavailableError

    age = (datetime.now(UTC) - observed_at).total_seconds()
    if not 0 <= age <= container.settings.live_max_age_seconds:
        raise DataSourceUnavailableError("live observation is stale or in the future")
    if container.settings.predictor_backend != "model":
        raise ModelNotReadyError("live forecasting requires a configured trained artifact")

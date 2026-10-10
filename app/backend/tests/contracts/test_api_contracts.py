from datetime import datetime

import pytest
from pydantic import ValidationError

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.prediction import PredictionResult, PredictRequest


def test_prediction_probability_is_bounded() -> None:
    with pytest.raises(ValidationError):
        PredictionResult(station_id="S001", eta=datetime.fromisoformat(
            "2026-10-13T16:40:00+07:00"), p_available=1.1,
                         reasons=[], explanation_method="rule", model_version="fake-v1",
                         data_type=DataType.MOCK, contract_version="0.1.0")


def test_predict_request_rejects_naive_time() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(station_id="S001", observed_at=datetime(2026, 10, 13, 16),
                       eta=datetime.fromisoformat("2026-10-13T16:40:00+07:00"),
                       connector_type="CCS2", scenario=Scenario.NORMAL)

from app.backend.contracts.enums import DataType
from app.backend.contracts.ports import Predictor
from app.backend.contracts.prediction import PredictionResult, PredictRequest


class FakePredictor:
    def predict(self, request: PredictRequest) -> PredictionResult:
        return PredictionResult(station_id=request.station_id, eta=request.eta, p_available=0.5,
                                 reasons=[], explanation_method="rule", model_version="fake-v1",
                                 data_type=DataType.MOCK)


def test_predictor_protocol_is_runtime_checkable() -> None:
    assert isinstance(FakePredictor(), Predictor)

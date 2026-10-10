from datetime import datetime

import pytest
from pydantic import ValidationError

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import PressureResponse, StatusWindow
from app.backend.contracts.simulation import ScenarioConfig, SimulationMetrics


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


def test_pressure_requires_known_scenario() -> None:
    with pytest.raises(ValidationError):
        PressureResponse.model_validate({
            "time": "2026-10-13T16:00:00+07:00", "scenario": "unknown", "stations": []
        })


def test_nested_status_window_is_strict_and_lags_nonnegative() -> None:
    with pytest.raises(ValidationError):
        StatusWindow.model_validate({
            "station_id": "S001", "observed_at": "2026-10-13T16:00:00+07:00",
            "lags": [-1], "statuses": [],
        })


def test_scenario_config_and_metrics_cross_field_checks() -> None:
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({"scenario": Scenario.NORMAL, "seed": 1,
                                       "start": "2026-10-13T17:00:00+07:00",
                                       "end": "2026-10-13T16:00:00+07:00", "step_minutes": 5,
                                       "demand_multiplier": 1, "compliance_rate": 1})
    with pytest.raises(ValidationError):
        SimulationMetrics(success_rate=0.5, mean_detour_km=1, mean_wait_minutes=1,
                          failed_count=2, vehicle_count=1)

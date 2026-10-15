from datetime import datetime
from math import isclose

from pydantic import Field, field_validator, model_validator

from .common import StrictModel
from .enums import DataType, Scenario
from .explanations import ModelExplanation


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


class PredictRequest(StrictModel):
    station_id: str = Field(min_length=1)
    observed_at: datetime
    eta: datetime
    connector_type: str = Field(min_length=1)
    scenario: Scenario

    _observed_aware = field_validator("observed_at")(classmethod(lambda cls, v: _aware(v)))
    _eta_aware = field_validator("eta")(classmethod(lambda cls, v: _aware(v)))

    @model_validator(mode="after")
    def eta_not_before_observed(self) -> "PredictRequest":
        if self.eta < self.observed_at:
            raise ValueError("eta must not precede observed_at")
        return self


class PredictionResult(StrictModel):
    station_id: str = Field(min_length=1)
    eta: datetime
    p_available: float = Field(ge=0, le=1)
    reasons: list[str]
    explanation_method: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    data_type: DataType
    contract_version: str = "0.1.0"
    explanation: ModelExplanation | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    _eta_aware = field_validator("eta")(classmethod(lambda cls, v: _aware(v)))

    @model_validator(mode="after")
    def explanation_matches_probability(self) -> "PredictionResult":
        if self.explanation is not None and self.explanation_method != "tree_shap_raw_margin":
            raise ValueError("structured TreeSHAP requires the matching explanation method")
        if self.explanation is not None and not isclose(
            self.explanation.calibrated_probability, self.p_available, rel_tol=1e-8, abs_tol=1e-8
        ):
            raise ValueError("explanation probability must match the forecast")
        return self
